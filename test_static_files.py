"""Test script to verify static files are accessible"""
import requests

def test_static_file():
    """Test if static file is accessible"""
    url = "http://localhost:8000/static/stripe/success.html?payment_success=true"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print("✅ SUCCESS: Static file is accessible!")
            print(f"Status Code: {response.status_code}")
            print(f"Content Length: {len(response.text)} bytes")
            return True
        else:
            print(f"❌ FAILED: Status Code {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print("Make sure the server is running on http://localhost:8000")
        return False

if __name__ == "__main__":
    print("Testing static file access...")
    print("URL: http://localhost:8000/static/stripe/success.html")
    print("-" * 50)
    test_static_file()
