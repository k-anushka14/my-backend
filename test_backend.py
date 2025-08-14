#!/usr/bin/env python3
"""
Test script for the Fake News Detection Backend
Run this after starting the backend to verify functionality
"""

import asyncio
import httpx
import json
import time
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = "default_api_key"  # Change this to your actual API key

class BackendTester:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"X-API-Key": api_key}
        )
    
    async def close(self):
        await self.client.aclose()
    
    async def test_health(self) -> bool:
        """Test the health endpoint."""
        try:
            print("🏥 Testing health endpoint...")
            response = await self.client.get(f"{self.base_url}/health")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health check passed: {data['status']}")
                print(f"   Services: {list(data['services'].keys())}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    async def test_root(self) -> bool:
        """Test the root endpoint."""
        try:
            print("🏠 Testing root endpoint...")
            response = await self.client.get(f"{self.base_url}/")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Root endpoint working: {data['message']}")
                print(f"   Version: {data['version']}")
                return True
            else:
                print(f"❌ Root endpoint failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Root endpoint error: {e}")
            return False
    
    async def test_text_analysis(self) -> bool:
        """Test the text analysis endpoint."""
        try:
            print("🔍 Testing text analysis endpoint...")
            
            # Test with suspicious text
            test_text = "The government is covering up the truth about vaccines. Wake up sheeple!"
            
            response = await self.client.post(
                f"{self.base_url}/analyze",
                json={"text": test_text}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Text analysis working:")
                print(f"   Score: {data['score']}/100")
                print(f"   Label: {data['label']}")
                print(f"   Reason: {data['reason']}")
                return True
            else:
                print(f"❌ Text analysis failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Text analysis error: {e}")
            return False
    
    async def test_fact_check(self) -> bool:
        """Test the fact-check endpoint."""
        try:
            print("📰 Testing fact-check endpoint...")
            
            # Test with a common query
            query = "COVID vaccine autism"
            
            response = await self.client.get(
                f"{self.base_url}/fact-check",
                params={"query": query}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Fact-check working:")
                print(f"   Source: {data['source']}")
                print(f"   Results: {data['total_results']}")
                if data['claims']:
                    print(f"   Sample claim: {data['claims'][0]['text'][:50]}...")
                return True
            else:
                print(f"❌ Fact-check failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Fact-check error: {e}")
            return False
    
    async def test_model_info(self) -> bool:
        """Test the model info endpoint."""
        try:
            print("🤖 Testing model info endpoint...")
            
            response = await self.client.get(f"{self.base_url}/model/info")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Model info working:")
                print(f"   Model: {data['model_name']}")
                print(f"   Loaded: {data['model_loaded']}")
                print(f"   Device: {data['device']}")
                return True
            else:
                print(f"❌ Model info failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Model info error: {e}")
            return False
    
    async def test_cache_status(self) -> bool:
        """Test the cache status endpoint."""
        try:
            print("💾 Testing cache status endpoint...")
            
            response = await self.client.get(f"{self.base_url}/cache/status")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Cache status working:")
                print(f"   Status: {data['status']}")
                if 'redis_info' in data:
                    print(f"   Redis version: {data['redis_info'].get('redis_version', 'unknown')}")
                return True
            else:
                print(f"❌ Cache status failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Cache status error: {e}")
            return False
    
    async def test_rate_limiting(self) -> bool:
        """Test rate limiting functionality."""
        try:
            print("⏱️ Testing rate limiting...")
            
            # Make multiple requests quickly
            responses = []
            for i in range(12):  # Should hit rate limit after 10
                try:
                    response = await self.client.get(f"{self.base_url}/health")
                    responses.append(response.status_code)
                    if i < 5:  # Only sleep for first few requests
                        await asyncio.sleep(0.1)
                except Exception as e:
                    responses.append(f"error: {e}")
            
            # Check if rate limiting worked
            success_count = sum(1 for r in responses if r == 200)
            print(f"   Successful requests: {success_count}/12")
            
            if success_count <= 10:
                print("✅ Rate limiting appears to be working")
                return True
            else:
                print("⚠️ Rate limiting may not be working properly")
                return False
                
        except Exception as e:
            print(f"❌ Rate limiting test error: {e}")
            return False
    
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all tests and return results."""
        print("🚀 Starting Fake News Backend Tests...")
        print("=" * 50)
        
        tests = [
            ("Health Check", self.test_health),
            ("Root Endpoint", self.test_root),
            ("Text Analysis", self.test_text_analysis),
            ("Fact Check", self.test_fact_check),
            ("Model Info", self.test_model_info),
            ("Cache Status", self.test_cache_status),
            ("Rate Limiting", self.test_rate_limiting),
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            print(f"\n{test_name}:")
            print("-" * 30)
            
            try:
                start_time = time.time()
                success = await test_func()
                end_time = time.time()
                
                results[test_name] = success
                
                if success:
                    print(f"⏱️  Time: {end_time - start_time:.2f}s")
                else:
                    print(f"⏱️  Time: {end_time - start_time:.2f}s (FAILED)")
                    
            except Exception as e:
                print(f"❌ Test crashed: {e}")
                results[test_name] = False
        
        return results
    
    def print_summary(self, results: Dict[str, bool]):
        """Print test results summary."""
        print("\n" + "=" * 50)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for success in results.values() if success)
        total = len(results)
        
        for test_name, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{test_name:20} {status}")
        
        print("-" * 50)
        print(f"Total: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Backend is working correctly.")
        elif passed > total // 2:
            print("⚠️  Some tests failed. Check the logs above.")
        else:
            print("💥 Many tests failed. Backend may not be running properly.")

async def main():
    """Main test function."""
    tester = BackendTester(BASE_URL, API_KEY)
    
    try:
        # Run all tests
        results = await tester.run_all_tests()
        
        # Print summary
        tester.print_summary(results)
        
    finally:
        await tester.close()

if __name__ == "__main__":
    print("🧪 Fake News Backend Test Suite")
    print("Make sure the backend is running on http://localhost:8000")
    print("Update API_KEY in this script if you've changed it from default")
    print()
    
    # Run tests
    asyncio.run(main())
