#!/usr/bin/env python3
"""
Phase 1 Automated Test Script for Banking System
Tests the two-tier client-server architecture (BC client + BAS server)
"""

import time
import subprocess
import sys
from threading import Thread
import Pyro5.api
from decimal import Decimal

# Add src to path
sys.path.insert(0, __file__.replace('\\', '/').rsplit('/', 1)[0])
from common import money, compute_fee


def wait_for_server(uri_str, timeout=10):
    """Wait for server to be ready."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            proxy = Pyro5.api.Proxy(uri_str)
            # Try a simple call to verify it's ready
            return proxy
        except Exception:
            time.sleep(0.5)
    raise Exception(f"Server did not start within {timeout} seconds")


def test_fee_calculation():
    """Test fee calculation against provided fee table."""
    print("\n" + "="*70)
    print("TEST 1: Fee Calculation")
    print("="*70)
    
    test_cases = [
        ("1000.00", "0.00", "Free tier"),
        ("2000.00", "0.00", "Boundary - still free"),
        ("2000.01", "5.00", "Entry tier minimum"),
        ("2500.00", "6.25", "Entry tier"),
        ("10000.00", "20.00", "Entry tier boundary (10000*0.0025=25, capped at 20)"),
        ("10000.01", "20.00", "Mid tier minimum"),
        ("20000.00", "25.00", "Mid tier boundary (20000*0.002=40, capped at 25)"),
        ("20000.01", "25.00", "Upper-mid tier minimum"),
        ("50000.00", "40.00", "Upper-mid tier boundary (50000*0.00125=62.50, capped at 40)"),
        ("50000.01", "40.00", "High tier minimum"),
        ("100000.00", "50.00", "High tier boundary (100000*0.0008=80, capped at 50)"),
        ("100000.01", "50.00", "Top tier minimum"),
        ("150000.00", "75.00", "Top tier"),
    ]
    
    passed = 0
    failed = 0
    
    for amount_str, expected, description in test_cases:
        amount = money(amount_str)
        fee = compute_fee(amount)
        expected_fee = money(expected)
        
        if fee == expected_fee:
            print(f"✓ {description:30} | Amount: ${amount_str:>12} | Fee: ${str(fee):>7}")
            passed += 1
        else:
            print(f"✗ {description:30} | Amount: ${amount_str:>12} | Fee: ${str(fee):>7} | Expected: ${expected:>7}")
            failed += 1
    
    print(f"\nFee calculation: {passed} passed, {failed} failed")
    return failed == 0


def test_server_operations(bas_uri):
    """Test server operations via RPC."""
    print("\n" + "="*70)
    print("TEST 2: Server Operations (RPC)")
    print("="*70)
    
    try:
        bas = wait_for_server(bas_uri)
        print(f"✓ Connected to BAS server at {bas_uri}")
    except Exception as e:
        print(f"✗ Failed to connect to server: {e}")
        return False
    
    all_passed = True
    
    # Test 1: Login with valid credentials
    print("\n--- Test 2.1: Login (Alice) ---")
    try:
        res = bas.login("alice", "alice123")
        if res.get("ok") and res.get("token"):
            token_alice = res["token"]
            print(f"✓ Alice login successful, token: {token_alice}")
        else:
            print(f"✗ Alice login failed: {res}")
            all_passed = False
    except Exception as e:
        print(f"✗ Alice login error: {e}")
        all_passed = False
        return False
    
    # Test 2: Login with invalid credentials
    print("\n--- Test 2.2: Login (Invalid) ---")
    try:
        res = bas.login("alice", "wrongpassword")
        if not res.get("ok"):
            print(f"✓ Invalid login correctly rejected: {res.get('error')}")
        else:
            print(f"✗ Invalid login should have failed but succeeded")
            all_passed = False
    except Exception as e:
        print(f"✗ Invalid login error: {e}")
        all_passed = False
    
    # Test 3: Bob login
    print("\n--- Test 2.3: Login (Bob) ---")
    try:
        res = bas.login("bob", "bob123")
        if res.get("ok") and res.get("token"):
            token_bob = res["token"]
            print(f"✓ Bob login successful, token: {token_bob}")
        else:
            print(f"✗ Bob login failed: {res}")
            all_passed = False
    except Exception as e:
        print(f"✗ Bob login error: {e}")
        all_passed = False
        return False
    
    # Test 4: Get balance (Alice)
    print("\n--- Test 2.4: Get Balance (Alice) ---")
    try:
        res = bas.get_balance(token_alice)
        if res.get("ok"):
            print(f"✓ Alice balance query successful: ${res.get('balance')}")
            alice_initial = money(res.get("balance", "0"))
        else:
            print(f"✗ Alice balance query failed: {res}")
            all_passed = False
    except Exception as e:
        print(f"✗ Alice balance query error: {e}")
        all_passed = False
    
    # Test 5: Get balance (Bob)
    print("\n--- Test 2.5: Get Balance (Bob) ---")
    try:
        res = bas.get_balance(token_bob)
        if res.get("ok"):
            print(f"✓ Bob balance query successful: ${res.get('balance')}")
            bob_initial = money(res.get("balance", "0"))
        else:
            print(f"✗ Bob balance query failed: {res}")
            all_passed = False
    except Exception as e:
        print(f"✗ Bob balance query error: {e}")
        all_passed = False
    
    # Test 6: Submit transfer (Alice to Bob)
    print("\n--- Test 2.6: Submit Transfer (Alice to Bob) ---")
    transfer_id = None
    try:
        amount_str = "100.00"
        res = bas.submit_transfer(token_alice, "bob", amount_str, "Test transfer")
        if res.get("ok"):
            transfer_id = res.get("transfer_id")
            fee = money(res.get("fee", "0"))
            print(f"✓ Transfer submitted successfully")
            print(f"  Transfer ID: {transfer_id}")
            print(f"  Fee: ${fee}")
            print(f"  New balance (Alice): ${res.get('sender_new_balance')}")
        else:
            print(f"✗ Transfer failed: {res.get('error')}")
            all_passed = False
    except Exception as e:
        print(f"✗ Transfer error: {e}")
        all_passed = False
    
    # Test 7: Get transfer status
    if transfer_id:
        print("\n--- Test 2.7: Get Transfer Status ---")
        try:
            res = bas.get_transfer_status(token_alice, transfer_id)
            if res.get("ok"):
                tr = res.get("transfer")
                print(f"✓ Transfer status retrieved:")
                print(f"  Status: {tr.get('status')}")
                print(f"  Amount: ${tr.get('amount')}")
                print(f"  Fee: ${tr.get('fee')}")
            else:
                print(f"✗ Transfer status query failed: {res}")
                all_passed = False
        except Exception as e:
            print(f"✗ Transfer status error: {e}")
            all_passed = False
    
    # Test 8: Insufficient funds
    print("\n--- Test 2.8: Insufficient Funds (Bob to Alice) ---")
    try:
        # Bob only has 1000, try to transfer 50000
        res = bas.submit_transfer(token_bob, "alice", "50000.00", "Too much")
        if not res.get("ok") and "Insufficient funds" in res.get("error", ""):
            print(f"✓ Insufficient funds correctly rejected: {res.get('error')}")
            failed_transfer_id = res.get("transfer_id")
            if failed_transfer_id:
                # Check status of failed transfer
                status_res = bas.get_transfer_status(token_bob, failed_transfer_id)
                if status_res.get("ok"):
                    tr = status_res.get("transfer")
                    print(f"✓ Failed transfer recorded with status: {tr.get('status')}")
        else:
            print(f"✗ Should have rejected insufficient funds: {res}")
            all_passed = False
    except Exception as e:
        print(f"✗ Insufficient funds test error: {e}")
        all_passed = False
    
    # Test 9: Invalid recipient
    print("\n--- Test 2.9: Invalid Recipient ---")
    try:
        res = bas.submit_transfer(token_alice, "nonexistent", "100.00", "Bad recipient")
        if not res.get("ok") and "Invalid recipient" in res.get("error", ""):
            print(f"✓ Invalid recipient correctly rejected: {res.get('error')}")
        else:
            print(f"✗ Should have rejected invalid recipient: {res}")
            all_passed = False
    except Exception as e:
        print(f"✗ Invalid recipient test error: {e}")
        all_passed = False
    
    # Test 10: Self-transfer
    print("\n--- Test 2.10: Self Transfer (Alice to Alice) ---")
    try:
        res = bas.submit_transfer(token_alice, "alice", "100.00", "Self transfer")
        if not res.get("ok") and "cannot be the sender" in res.get("error", "").lower():
            print(f"✓ Self-transfer correctly rejected: {res.get('error')}")
        else:
            print(f"✗ Should have rejected self-transfer: {res}")
            all_passed = False
    except Exception as e:
        print(f"✗ Self-transfer test error: {e}")
        all_passed = False
    
    # Test 11: Invalid token
    print("\n--- Test 2.11: Invalid Token ---")
    try:
        res = bas.get_balance("fake_token_12345")
        if not res.get("ok"):
            print(f"✓ Invalid token correctly rejected: {res.get('error')}")
        else:
            print(f"✗ Should have rejected invalid token: {res}")
            all_passed = False
    except Exception as e:
        # Some implementations might raise an exception instead
        if "Unauthorized" in str(e) or "token" in str(e).lower():
            print(f"✓ Invalid token correctly rejected: {e}")
        else:
            print(f"✗ Invalid token test error: {e}")
            all_passed = False
    
    return all_passed


def main():
    print("\n" + "="*70)
    print("PHASE 1 BANKING SYSTEM - AUTOMATED TEST SUITE")
    print("="*70)
    print("Testing: Two-tier architecture (BC Client + BAS Server)")
    print("RPC Mechanism: Pyro5")
    
    # Test 1: Fee calculation
    fee_test_passed = test_fee_calculation()
    
    # Test 2: Server operations (requires running server)
    print("\n" + "="*70)
    print("Starting BAS Server for RPC tests...")
    print("="*70)
    
    # Start server in background
    server_process = subprocess.Popen(
        [sys.executable, "src/bas_server.py"],
        cwd=__file__.replace('\\', '/').rsplit('/', 1)[0].rsplit('/', 1)[0],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Wait a bit for server to start
        time.sleep(2)
        
        # Try to extract URI from server output (simplified approach)
        # Using default Pyro5 daemon port
        bas_uri = "PYRO:BAS@127.0.0.1:9090"
        
        server_test_passed = test_server_operations(bas_uri)
    finally:
        # Terminate server
        server_process.terminate()
        try:
            server_process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            server_process.kill()
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Fee Calculation Tests: {'PASSED' if fee_test_passed else 'FAILED'}")
    print(f"Server Operations Tests: {'PASSED' if server_test_passed else 'FAILED'}")
    
    overall = fee_test_passed and server_test_passed
    print(f"\nOverall Result: {'ALL TESTS PASSED ✓' if overall else 'SOME TESTS FAILED ✗'}")
    print("="*70 + "\n")
    
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
