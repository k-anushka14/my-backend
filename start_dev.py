#!/usr/bin/env python3
"""
Development startup script for Fake News Detection Backend
This script helps set up the development environment and start services
"""

import os
import sys
import subprocess
import time
import asyncio
import httpx
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ is required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def check_dependencies():
    """Check if required packages are installed."""
    required_packages = [
        'fastapi', 'uvicorn', 'redis', 'httpx', 
        'transformers', 'torch', 'beautifulsoup4'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} (missing)")
    
    if missing_packages:
        print(f"\n📦 Install missing packages:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
    return True

def check_env_file():
    """Check if .env file exists and create from template if needed."""
    env_file = Path('.env')
    env_example = Path('env.example')
    
    if not env_file.exists():
        if env_example.exists():
            print("📝 Creating .env file from template...")
            try:
                with open(env_example, 'r') as f:
                    content = f.read()
                
                with open(env_file, 'w') as f:
                    f.write(content)
                
                print("✅ .env file created")
                print("⚠️  Please edit .env file with your actual configuration")
                return False
            except Exception as e:
                print(f"❌ Failed to create .env file: {e}")
                return False
        else:
            print("❌ No .env file found and no template available")
            return False
    else:
        print("✅ .env file exists")
        return True

def check_redis():
    """Check if Redis is running."""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, socket_connect_timeout=1)
        r.ping()
        print("✅ Redis is running")
        return True
    except Exception as e:
        print("❌ Redis is not running")
        print("   Start Redis with: redis-server")
        print("   Or use Docker: docker run -d -p 6379:6379 redis:7-alpine")
        return False

def start_redis_docker():
    """Start Redis using Docker if available."""
    try:
        print("🐳 Starting Redis with Docker...")
        subprocess.run([
            'docker', 'run', '-d', 
            '--name', 'fake-news-redis',
            '-p', '6379:6379',
            'redis:7-alpine'
        ], check=True, capture_output=True)
        
        # Wait for Redis to start
        time.sleep(3)
        
        if check_redis():
            print("✅ Redis started successfully")
            return True
        else:
            print("❌ Redis failed to start")
            return False
            
    except subprocess.CalledProcessError:
        print("❌ Failed to start Redis with Docker")
        return False
    except FileNotFoundError:
        print("❌ Docker not found")
        return False

async def test_backend():
    """Test if the backend is responding."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8000/health")
            if response.status_code == 200:
                print("✅ Backend is responding")
                return True
            else:
                print(f"❌ Backend responded with status {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Backend not responding: {e}")
        return False

def start_backend():
    """Start the backend server."""
    print("🚀 Starting Fake News Detection Backend...")
    
    try:
        # Start the backend in a subprocess
        process = subprocess.Popen([
            sys.executable, 'app.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a bit for startup
        time.sleep(5)
        
        # Check if process is still running
        if process.poll() is None:
            print("✅ Backend started successfully")
            print("   URL: http://localhost:8000")
            print("   Health: http://localhost:8000/health")
            print("   Docs: http://localhost:8000/docs")
            print("\n   Press Ctrl+C to stop the backend")
            
            try:
                process.wait()
            except KeyboardInterrupt:
                print("\n🛑 Stopping backend...")
                process.terminate()
                process.wait()
                print("✅ Backend stopped")
        else:
            stdout, stderr = process.communicate()
            print("❌ Backend failed to start")
            print("STDOUT:", stdout.decode())
            print("STDERR:", stderr.decode())
            return False
            
    except Exception as e:
        print(f"❌ Failed to start backend: {e}")
        return False
    
    return True

def main():
    """Main startup function."""
    print("🚀 Fake News Detection Backend - Development Setup")
    print("=" * 60)
    
    # Check Python version
    if not check_python_version():
        return 1
    
    print("\n📦 Checking dependencies...")
    if not check_dependencies():
        print("\n💡 Install dependencies first:")
        print("   pip install -r requirements.txt")
        return 1
    
    print("\n🔧 Checking environment...")
    if not check_env_file():
        print("\n⚠️  Please configure your .env file before continuing")
        return 1
    
    print("\n🗄️ Checking Redis...")
    if not check_redis():
        print("\n🐳 Attempting to start Redis with Docker...")
        if not start_redis_docker():
            print("\n💡 Please start Redis manually:")
            print("   - Install Redis: https://redis.io/download")
            print("   - Or use Docker: docker run -d -p 6379:6379 redis:7-alpine")
            return 1
    
    print("\n🧪 Testing backend...")
    if asyncio.run(test_backend()):
        print("✅ Backend is already running")
        return 0
    
    print("\n🚀 Starting backend...")
    if start_backend():
        return 0
    else:
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Setup interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)

