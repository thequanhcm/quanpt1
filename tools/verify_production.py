"""
Production Verification Script
Verifies all components are working correctly after deployment
"""

import sys
import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, List, Tuple

class ProductionVerifier:
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'environment': 'production',
            'checks': [],
            'summary': {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'warnings': 0
            }
        }
    
    def check_endpoint(self, name: str, url: str, expected_status: int = 200) -> bool:
        """Check if an endpoint is responding"""
        try:
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=10) as response:
                status = response.status
                if status == expected_status:
                    self._log_check(name, 'PASS', f'HTTP {status}')
                    return True
                else:
                    self._log_check(name, 'FAIL', f'Expected {expected_status}, got {status}')
                    return False
        except urllib.error.URLError as e:
            self._log_check(name, 'FAIL', f'Connection error: {str(e)}')
            return False
        except Exception as e:
            self._log_check(name, 'FAIL', f'Error: {str(e)}')
            return False
    
    def check_database(self) -> bool:
        """Check database connectivity and basic operations"""
        try:
            from sqlalchemy import create_engine, text
            from dotenv import load_dotenv
            import os
            
            load_dotenv()
            db_url = os.getenv('DATABASE_URL', 'sqlite:///brain.db')
            
            engine = create_engine(db_url)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            self._log_check('Database Connectivity', 'PASS', 'Connected successfully')
            
            # Check tables exist
            with engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                ))
                count = result.scalar()
                self._log_check('Database Tables', 'PASS', f'{count} tables found')
            
            return True
            
        except Exception as e:
            self._log_check('Database', 'FAIL', str(e))
            return False
    
    def check_redis(self) -> bool:
        """Check Redis connectivity"""
        try:
            import redis
            from dotenv import load_dotenv
            import os
            
            load_dotenv()
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            
            r = redis.from_url(redis_url)
            r.ping()
            
            self._log_check('Redis', 'PASS', 'Connected and ping successful')
            return True
            
        except ImportError:
            self._log_check('Redis', 'WARNING', 'redis-py not installed')
            return False
        except Exception as e:
            self._log_check('Redis', 'FAIL', str(e))
            return False
    
    def check_processes(self) -> bool:
        """Check if all required processes are running"""
        import psutil
        
        required_ports = [8216, 8765, 18036, 17236, 7724]
        all_ok = True
        
        for port in required_ports:
            try:
                conn = urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health', timeout=5)
                self._log_check(f'Port {port}', 'PASS', 'Listening')
            except:
                self._log_check(f'Port {port}', 'FAIL', 'Not listening')
                all_ok = False
        
        return all_ok
    
    def check_disk_space(self, min_gb: float = 10.0) -> bool:
        """Check available disk space"""
        import shutil
        
        total, used, free = shutil.disk_usage("C:\\")
        free_gb = free / (2**30)
        
        if free_gb >= min_gb:
            self._log_check('Disk Space', 'PASS', f'{free_gb:.1f} GB free')
            return True
        else:
            self._log_check('Disk Space', 'FAIL', f'Only {free_gb:.1f} GB free (need {min_gb} GB)')
            return False
    
    def check_memory(self, min_gb: float = 4.0) -> bool:
        """Check available memory"""
        import psutil
        
        memory = psutil.virtual_memory()
        available_gb = memory.available / (2**30)
        
        if available_gb >= min_gb:
            self._log_check('Memory', 'PASS', f'{available_gb:.1f} GB available')
            return True
        else:
            self._log_check('Memory', 'WARNING', f'Only {available_gb:.1f} GB available')
            return True  # Warning, not fail
    
    def check_python_version(self) -> bool:
        """Check Python version"""
        required_version = (3, 10)
        current_version = sys.version_info
        
        if current_version >= required_version:
            version_str = f"{current_version.major}.{current_version.minor}.{current_version.micro}"
            self._log_check('Python Version', 'PASS', f'{version_str}')
            return True
        else:
            self._log_check('Python Version', 'FAIL', f'Need {required_version[0]}.{required_version[1]}+, got {current_version.major}.{current_version.minor}')
            return False
    
    def check_dependencies(self) -> bool:
        """Check required packages are installed"""
        required_packages = [
            'flask', 'sqlalchemy', 'redis', 'psycopg2',
            'python-dotenv', 'requests', 'pytest'
        ]
        
        all_ok = True
        for package in required_packages:
            try:
                __import__(package)
                self._log_check(f'Package: {package}', 'PASS', 'Installed')
            except ImportError:
                self._log_check(f'Package: {package}', 'FAIL', 'Not installed')
                all_ok = False
        
        return all_ok
    
    def _log_check(self, name: str, status: str, message: str):
        """Log a check result"""
        self.results['checks'].append({
            'name': name,
            'status': status,
            'message': message
        })
        
        self.results['summary']['total'] += 1
        if status == 'PASS':
            self.results['summary']['passed'] += 1
        elif status == 'FAIL':
            self.results['summary']['failed'] += 1
        else:
            self.results['summary']['warnings'] += 1
    
    def run_all_checks(self) -> Dict:
        """Run all verification checks"""
        print("=" * 60)
        print("QUAN AI BRAIN - Production Verification")
        print("=" * 60)
        print()
        
        checks = [
            ('Python Version', self.check_python_version),
            ('Disk Space', self.check_disk_space),
            ('Memory', self.check_memory),
            ('Database', self.check_database),
            ('Redis', self.check_redis),
            ('Dependencies', self.check_dependencies),
            ('Services Health', lambda: all([
                self.check_endpoint('API Server', 'http://127.0.0.1:8216/api/health'),
                self.check_endpoint('Dashboard', 'http://127.0.0.1:8765/api/health'),
                self.check_endpoint('Responder', 'http://127.0.0.1:18036/api/health'),
                self.check_endpoint('Watchdog', 'http://127.0.0.1:17236/api/health')
            ]))
        ]
        
        for name, check_func in checks:
            try:
                check_func()
            except Exception as e:
                self._log_check(name, 'FAIL', f'Exception: {str(e)}')
        
        # Print summary
        print()
        print("=" * 60)
        print("VERIFICATION SUMMARY")
        print("=" * 60)
        print(f"Total Checks: {self.results['summary']['total']}")
        print(f"Passed:       {self.results['summary']['passed']} ✓")
        print(f"Failed:       {self.results['summary']['failed']} ✗")
        print(f"Warnings:     {self.results['summary']['warnings']} ⚠")
        print("=" * 60)
        
        # Print detailed results
        print()
        print("DETAILED RESULTS:")
        print("-" * 60)
        for check in self.results['checks']:
            status_icon = {
                'PASS': '✓',
                'FAIL': '✗',
                'WARNING': '⚠'
            }.get(check['status'], '?')
            
            print(f"{status_icon} {check['name']}: {check['status']} - {check['message']}")
        
        print("-" * 60)
        
        # Save results
        with open('logs/verification_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print()
        print(f"Results saved to: logs/verification_results.json")
        
        # Return success if no failures
        return self.results['summary']['failed'] == 0


def main():
    verifier = ProductionVerifier()
    success = verifier.run_all_checks()
    
    if success:
        print()
        print("🎉 ALL CHECKS PASSED - System is ready for production!")
        sys.exit(0)
    else:
        print()
        print("❌ SOME CHECKS FAILED - Please review and fix issues")
        sys.exit(1)


if __name__ == '__main__':
    main()