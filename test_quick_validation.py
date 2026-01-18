#!/usr/bin/env python3
"""
Phase 1 Quick Validation Script
Validates the core components are working
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from common import money, compute_fee

def test_fee_calculation():
    """Validate all fee calculations"""
    test_cases = [
        ("1000.00", "0.00"),
        ("2000.00", "0.00"),
        ("2000.01", "5.00"),
        ("2500.00", "6.25"),
        ("10000.00", "20.00"),
        ("10000.01", "20.00"),
        ("20000.00", "25.00"),
        ("20000.01", "25.00"),
        ("50000.00", "40.00"),
        ("50000.01", "40.00"),
        ("100000.00", "50.00"),
        ("100000.01", "50.00"),
        ("150000.00", "75.00"),
    ]
    
    print("✓ Fee Calculation Tests:")
    for amount_str, expected in test_cases:
        amount = money(amount_str)
        fee = compute_fee(amount)
        expected_fee = money(expected)
        assert fee == expected_fee, f"Fee mismatch for {amount_str}: got {fee}, expected {expected_fee}"
        print(f"  ✓ ${amount_str:>12} → ${str(fee):>7}")
    
    print(f"\n✓ All {len(test_cases)} fee calculation tests passed!")
    return True

def test_imports():
    """Verify all modules can be imported"""
    print("\n✓ Import Tests:")
    try:
        import Pyro5.api
        print("  ✓ Pyro5.api imported successfully")
    except ImportError as e:
        print(f"  ✗ Failed to import Pyro5.api: {e}")
        return False
    
    try:
        from bas_server import BankApplicationServer
        print("  ✓ BankApplicationServer imported successfully")
    except ImportError as e:
        print(f"  ✗ Failed to import BankApplicationServer: {e}")
        return False
    
    return True

def test_server_initialization():
    """Verify server initializes correctly"""
    print("\n✓ Server Initialization Test:")
    try:
        from bas_server import BankApplicationServer
        server = BankApplicationServer()
        print("  ✓ BAS server instance created")
        print(f"  ✓ Mock users initialized: {list(server.users.keys())}")
        print(f"  ✓ Mock balances initialized:")
        for user, balance in server.balances.items():
            print(f"    - {user}: ${balance}")
        return True
    except Exception as e:
        print(f"  ✗ Server initialization failed: {e}")
        return False

def main():
    print("="*70)
    print("PHASE 1 - QUICK VALIDATION")
    print("="*70)
    
    all_passed = True
    all_passed = test_imports() and all_passed
    all_passed = test_server_initialization() and all_passed
    all_passed = test_fee_calculation() and all_passed
    
    print("\n" + "="*70)
    if all_passed:
        print("✓ ALL VALIDATIONS PASSED - PHASE 1 IS READY")
    else:
        print("✗ Some validations failed")
    print("="*70 + "\n")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
