# Banking System - Phase 1

## Overview

This is a two-tier distributed banking system implementation using Pyro5 RPC (Remote Procedure Call).

**Architecture:**
- **Client Tier:** Banking Client (BC client) - Customer-facing interface
- **Application Tier:** Bank Application Server (BAS server) - Business logic and state management
- **Storage:** In-memory (Phase 1)

## Quick Start

### Prerequisites
```bash
pip install -r requirements.txt
```

This installs Pyro5 5.16.

### Running Phase 1

**Terminal 1 - Start the BAS Server:**
```bash
python src/bas_server.py
```

Output:
```
BAS server running.
URI: PYRO:BAS@127.0.0.1:60943
Object name: BAS
Keep this terminal open.
```

Copy the URI from the server output.

**Terminal 2 - Run the BC Client:**
```bash
python src/bc_client.py
```

When prompted, paste the URI from the server output.

### Features Implemented

✅ **Login & Authentication**
- Mock username/password authentication
- Session token management
- Token validation for subsequent requests

✅ **Balance Query**
- Authenticated balance retrieval
- Current balances: Alice $50,000, Bob $1,000

✅ **Transfer Request Submission**
- Sender validation
- Recipient validation
- Amount validation
- Fee calculation using tiered fee structure
- Sufficient funds check
- Atomic balance updates
- Transfer status tracking

✅ **Transfer Fee Structure**
| Amount Range | Percentage | Cap |
|---|---|---|
| $0 – $2,000.00 | 0% | — |
| $2,000.01 – $10,000.00 | 0.25% | $20.00 |
| $10,000.01 – $20,000.00 | 0.20% | $25.00 |
| $20,000.01 – $50,000.00 | 0.125% | $40.00 |
| $50,000.01 – $100,000.00 | 0.08% | $50.00 |
| $100,000.01 and above | 0.05% | $100.00 |

✅ **Transfer Status Query**
- Query by transfer ID
- Status tracking: PENDING, COMPLETED, FAILED
- Transaction history

### Testing

**Run validation tests:**
```bash
python test_quick_validation.py
```

This validates:
- All imports and dependencies
- Server initialization
- Fee calculation correctness
- Mock data setup

## System Behaviors

### Login
```
Username: alice
Password: alice123
→ Returns: session token
```

### Balance Query
```
Token: [session_token]
→ Returns: current account balance
```

### Submit Transfer
```
Token: [session_token]
Recipient: bob
Amount: 100.00
Reference: Test transfer (optional)
→ Returns: transfer_id, fee, new balance, status
```

### Transfer Status Query
```
Token: [session_token]
Transfer ID: tr_abc123def456
→ Returns: transfer details including status
```

## Implementation Details

### Files

- **`src/bas_server.py`** - BAS server with RPC methods
  - In-memory user/account storage
  - Token-based session management
  - Transfer processing and state management
  
- **`src/bc_client.py`** - BC client interface
  - Menu-driven user interface
  - RPC calls to BAS server
  - Interactive session management

- **`src/common.py`** - Shared utilities
  - Decimal money handling (proper rounding)
  - Fee calculation logic
  - ID generation (transfer IDs, tokens)

- **`test_quick_validation.py`** - Validation script
  - Imports verification
  - Fee calculation testing
  - Server initialization testing

### Design Choices

1. **Synchronous RPC (Pyro5)**: Chosen for simplicity and consistency with assignment requirements. All operations use request/response pattern.

2. **In-Memory State (Phase 1)**: Simplified for Phase 1. All data stored in BAS server memory:
   - User credentials
   - Account balances
   - Transfer records

3. **Token-Based Authentication**: Simple session tokens for authenticated requests. Tokens are hex-encoded random strings.

4. **Atomic Operations**: Balance updates applied atomically after all validation passes.

5. **Fee Calculation**: Implemented as two-step process:
   - Calculate fee as percentage of amount
   - Apply per-transfer cap (maximum fee)

### Error Handling

- Invalid credentials → Login rejected
- Invalid token → Operation rejected with 401 error
- Invalid recipient → Transfer rejected
- Insufficient funds → Transfer marked FAILED, recorded
- Self-transfer → Rejected
- Invalid amount → Rejected

## Next Steps (Phase 2)

Phase 2 will add:
- Database tier (BDB server) with SQLite
- Persistent storage of all data
- Three-tier architecture
- Enhanced testing and validation

## Notes

- This is a teaching system with mock data only
- No real money or actual banking integration
- For development/testing purposes only
