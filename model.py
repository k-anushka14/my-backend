import asyncio
import re
from typing import Dict, List, Optional, Tuple
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch
from config import settings
from cache import cache

class FakeNewsDetector:
    """AI-powered fake news detection service using HuggingFace models."""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self._model_loaded = False
        self._loading_lock = asyncio.Lock()
        
        # Suspicious keywords and patterns
        self.suspicious_keywords = [
            'conspiracy', 'cover up', 'fake news', 'hoax', 'lies',
            'mainstream media', 'sheeple', 'wake up', 'truth seekers',
            'government lies', 'big pharma', 'deep state', 'illuminati',
            'vaccine autism', '5g coronavirus', 'flat earth', 'moon landing fake'
        ]
        
        self.suspicious_patterns = [
            r'\b(?:100%|absolutely|definitely|proven|scientific)\s+(?:fact|truth|real)\b',
            r'\b(?:mainstream|corporate|fake)\s+(?:media|news|scientists)\b',
            r'\b(?:they|them|them)\s+(?:don\'t|won\'t|can\'t)\s+(?:want|let|tell)\s+(?:you|us)\b',
            r'\b(?:wake\s+up|open\s+your\s+eyes|do\s+your\s+research)\b',
            r'\b(?:sheeple|sheep|brainwashed|programmed)\b'
        ]
    
    async def load_model(self):
        """Load the model asynchronously with singleton pattern."""
        if self._model_loaded:
            return
        
        async with self._loading_lock:
            if self._model_loaded:  # Double-check pattern
                return
            
            try:
                print(f"🔄 Loading model: {settings.MODEL_NAME}")
                
                # Load tokenizer and model
                self.tokenizer = AutoTokenizer.from_pretrained(settings.MODEL_NAME)
                self.model = AutoModelForSequenceClassification.from_pretrained(settings.MODEL_NAME)
                
                # Create pipeline
                self.pipeline = pipeline(
                    "text-classification",
                    model=self.model,
                    tokenizer=self.tokenizer,
                    device=0 if torch.cuda.is_available() else -1
                )
                
                self._model_loaded = True
                print("✅ Model loaded successfully")
                
            except Exception as e:
                print(f"❌ Model loading failed: {e}")
                # Fallback to a simpler approach if model loading fails
                self._model_loaded = False
    
    def _sanitize_text(self, text: str) -> str:
        """Sanitize input text to prevent XSS and other attacks."""
        if not text or not isinstance(text, str):
            return ""
        
        # Remove potentially dangerous HTML/script tags
        text = re.sub(r'<[^>]*>', '', text)
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        text = re.sub(r'data:', '', text, flags=re.IGNORECASE)
        
        # Limit text length
        text = text[:10000]  # Max 10KB
        
        # Basic text cleaning
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _detect_suspicious_patterns(self, text: str) -> Tuple[bool, List[str]]:
        """Detect suspicious patterns and keywords in text."""
        text_lower = text.lower()
        detected_patterns = []
        
        # Check for suspicious keywords
        for keyword in self.suspicious_keywords:
            if keyword in text_lower:
                detected_patterns.append(f"keyword_match:{keyword}")
        
        # Check for suspicious patterns
        for pattern in self.suspicious_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                detected_patterns.append(f"pattern_match:{pattern}")
        
        return len(detected_patterns) > 0, detected_patterns
    
    def _calculate_credibility_score(self, model_score: float, suspicious_detected: bool, 
                                   pattern_count: int) -> Tuple[int, str]:
        """Calculate final credibility score and label."""
        # Base score from model (assuming model returns 0-1, where 1 is fake)
        base_score = int(model_score * 100)
        
        # Adjust score based on suspicious patterns
        if suspicious_detected:
            base_score += min(pattern_count * 10, 30)  # Max 30 points for patterns
        
        # Ensure score is within 0-100 range
        final_score = max(0, min(100, base_score))
        
        # Determine label
        if final_score < 30:
            label = "reliable"
        elif final_score < 70:
            label = "suspicious"
        else:
            label = "fake"
        
        return final_score, label
    
    async def analyze_text(self, text: str) -> Dict:
        """Analyze text for fake news detection."""
        # Sanitize input
        sanitized_text = self._sanitize_text(text)
        if not sanitized_text:
            return {
                "error": "Invalid or empty text input",
                "score": 0,
                "label": "unknown",
                "reason": "invalid_input"
            }
        
        # Check cache first
        cached_result = await cache.get_model_prediction(sanitized_text)
        if cached_result:
            return cached_result
        
        try:
            # Ensure model is loaded
            await self.load_model()
            
            if not self._model_loaded:
                # Fallback to pattern-based detection
                return await self._fallback_analysis(sanitized_text)
            
            # Get model prediction
            model_result = self.pipeline(sanitized_text, truncation=True, max_length=512)
            
            # Extract model score (assuming binary classification: fake vs real)
            model_score = model_result[0]['score']
            if model_result[0]['label'] == 'LABEL_0':  # Assuming LABEL_0 is real
                model_score = 1 - model_score
            
            # Detect suspicious patterns
            suspicious_detected, patterns = self._detect_suspicious_patterns(sanitized_text)
            
            # Calculate final score and label
            final_score, label = self._calculate_credibility_score(
                model_score, suspicious_detected, len(patterns)
            )
            
            # Determine reason
            if patterns:
                reason = f"pattern_detection:{','.join(patterns[:3])}"  # Limit to 3 patterns
            elif model_score > 0.8:
                reason = "high_model_confidence"
            elif model_score > 0.6:
                reason = "moderate_model_confidence"
            else:
                reason = "low_risk_patterns"
            
            result = {
                "score": final_score,
                "label": label,
                "reason": reason,
                "model_confidence": round(model_score, 3),
                "patterns_detected": len(patterns),
                "text_length": len(sanitized_text)
            }
            
            # Cache the result
            await cache.set_model_prediction(sanitized_text, result)
            
            return result
            
        except Exception as e:
            print(f"Model analysis error: {e}")
            # Fallback to pattern-based detection
            return await self._fallback_analysis(sanitized_text)
    
    async def _fallback_analysis(self, text: str) -> Dict:
        """Fallback analysis when model is not available."""
        suspicious_detected, patterns = self._detect_suspicious_patterns(text)
        
        if suspicious_detected:
            score = min(60 + len(patterns) * 10, 90)
            label = "suspicious" if score < 80 else "fake"
            reason = f"fallback_pattern_detection:{','.join(patterns[:3])}"
        else:
            score = 20
            label = "reliable"
            reason = "fallback_low_risk"
        
        return {
            "score": score,
            "label": label,
            "reason": reason,
            "model_confidence": None,
            "patterns_detected": len(patterns),
            "text_length": len(text),
            "fallback_mode": True
        }
    
    def get_model_info(self) -> Dict:
        """Get information about the loaded model."""
        return {
            "model_name": settings.MODEL_NAME,
            "model_loaded": self._model_loaded,
            "device": "cuda" if torch.cuda.is_available() else "cpu",
            "cuda_available": torch.cuda.is_available(),
            "model_size_mb": self._get_model_size() if self.model else None
        }
    
    def _get_model_size(self) -> Optional[float]:
        """Calculate model size in MB."""
        try:
            if self.model:
                param_size = 0
                for param in self.model.parameters():
                    param_size += param.nelement() * param.element_size()
                buffer_size = 0
                for buffer in self.model.buffers():
                    buffer_size += buffer.nelement() * buffer.element_size()
                size_mb = (param_size + buffer_size) / 1024 / 1024
                return round(size_mb, 2)
        except:
            pass
        return None

# Global model instance
fake_news_detector = FakeNewsDetector()
