# Banking System - Phase 2

## Overview

This is a three-tier distributed banking system with persistent storage using SQLite.

**Architecture:**
- **Client Tier:** Banking Client (BC client) - Customer-facing interface
- **Application Tier:** Bank Application Server (BAS server) - Business logic and RPC interface
- **Data Tier:** Bank Database Server (BDB server) - SQLite persistence layer

## Phase 2 Improvements

### From Phase 1 → Phase 2

| Aspect | Phase 1 | Phase 2 |
|--------|---------|---------|
| Storage | In-memory (dict) | SQLite database |
| Persistence | No | Yes ✓ |
| Audit Trail | No | Yes ✓ |
| Architecture | 2-tier | 3-tier ✓ |
| Scalability | Single server | Database separation ✓ |

## Running Phase 2

### Prerequisites
```bash
pip install -r requirements.txt
```

Requires: Pyro5 5.16, sqlite3 (built-in)

### Startup Order (Important!)

**Terminal 1 - Start BDB Server (Database):**
```bash
python src/bdb_server.py
```

Output:
```
BDB server running.
URI: PYRO:BDB@127.0.0.1:9091
Object name: BDB
Database file: banking.db
Keep this terminal open.
```

**Terminal 2 - Start BAS Server (Application):**
```bash
python src/bas_server.py
```

Output:
```
BAS server running.
URI: PYRO:BAS@127.0.0.1:9090
Object name: BAS
Connected to BDB at: PYRO:BDB@127.0.0.1:9091
Keep this terminal open.
```

**Terminal 3 - Run BC Client:**
```bash
python src/bc_client.py
```

When prompted, paste the BAS URI from Terminal 2.

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    email TEXT,
    created_at INTEGER
)
```

### Accounts Table
```sql
CREATE TABLE accounts (
    username TEXT PRIMARY KEY,
    balance TEXT NOT NULL,
    created_at INTEGER,
    FOREIGN KEY (username) REFERENCES users(username)
)
```

### Transfers Table
```sql
CREATE TABLE transfers (
    transfer_id TEXT PRIMARY KEY,
    from_user TEXT NOT NULL,
    to_user TEXT NOT NULL,
    amount TEXT NOT NULL,
    fee TEXT NOT NULL,
    reference TEXT,
    status TEXT NOT NULL,
    reason TEXT,
    created_at INTEGER,
    updated_at INTEGER
)
```

### Audit Logs Table
```sql
CREATE TABLE audit_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation TEXT NOT NULL,
    username TEXT,
    details TEXT,
    timestamp INTEGER
)
```

## Components

### BDB Server (src/bdb_server.py)
Database tier - manages all persistent data via SQLite

**RPC Methods:**
- `get_user(username)` - Get user info
- `verify_user(username, password)` - Authenticate user
- `create_user(username, password, email)` - Create new account
- `get_balance(username)` - Get account balance
- `update_balance(username, new_balance)` - Update balance
- `create_transfer(transfer_record)` - Record transfer
- `get_transfer(transfer_id)` - Get transfer by ID
- `update_transfer(transfer_id, status, reason)` - Update transfer status
- `get_transfers_by_user(username)` - Get user's transfers
- `get_audit_logs(limit)` - Get audit trail
- `health_check()` - Server status

### BAS Server (src/bas_server.py)
Application tier - business logic and RPC interface for clients

**RPC Methods:**
- `login(username, password)` - Authenticate and get session token
- `get_balance(token)` - Get authenticated user's balance
- `submit_transfer(token, recipient, amount, reference)` - Submit transfer
- `get_transfer_status(token, transfer_id)` - Query transfer status

**Features:**
- Session/token management
- Fee calculation
- Transfer validation
- Communication with BDB

### BC Client (src/bc_client.py)
Client tier - user-facing interface

**User Workflows:**
1. Login
2. View balance
3. Submit transfer
4. Query transfer status
5. Logout

## Mock Data

**Pre-initialized users:**
- Alice: password = "alice123", balance = $50,000.00
- Bob: password = "bob123", balance = $1,000.00

## Design Features

### Persistent Storage
- All data persisted to SQLite database
- Database survives server restarts
- Audit trail of all operations

### Atomic Transactions
- Transfer updates atomic via SQLite transactions
- Balance updates only on successful fund transfer
- Consistent state across BDB operations

### Security
- Password hashing (SHA-256)
- Token-based authentication for transfers
- Token validation on each operation
- Audit logging of all access

### Separation of Concerns
- BC client → no direct DB access
- BAS → business logic + session mgmt
- BDB → data persistence only

### Error Handling
- Connection failures caught
- Transaction rollback on errors
- Meaningful error messages
- Graceful degradation

## Testing

**Unit Tests (Manual):**
```bash
# Test BDB database operations
python -c "from src.bdb_server import BankDatabaseServer; bdb = BankDatabaseServer(); print('✓ BDB initialized')"

# Test BAS with BDB
python src/test_phase1.py  # Updated for Phase 2
```

**Integration Testing:**
1. Start all three servers in order
2. Use BC client to perform transfers
3. Restart BDB/BAS - data persists!
4. Verify transfers in database

## File Structure

```
src/
├── bdb_server.py      (NEW) Database server with SQLite
├── bas_server.py      (MODIFIED) Now uses BDB instead of in-memory
├── bc_client.py       (Updated) Type hints improved
├── common.py          (Same) Shared utilities
├── test_phase1.py     (Existing) Fee calculation tests
└── __pycache__/       Auto-generated

banking.db            (NEW) SQLite database file
```

## Known Limitations

- Password hashing is simple (SHA-256 only, no salt)
- No transaction queue for long-running operations
- No cluster support (single BDB server)
- No read replicas for scaling

## Next Steps / Future Enhancements

- Add concurrent request handling with queues
- Implement more robust authentication (bcrypt)
- Add transfer notifications/emails
- Read replicas for scaling
- Database encryption
- Scheduled audit log cleanup

## Troubleshooting

**"Cannot connect to BDB"**
- Ensure BDB server is running on port 9091
- Check firewall settings
- Verify "PYRO:BDB@127.0.0.1:9091" in BAS startup

**"Database locked"**
- SQLite limitation with concurrent writes
- Short operations minimize lock time
- Consider timeout settings

**"Account not found"**
- Check user exists in database
- Verify credentials match
- Check audit logs for creation

## Database Queries

### Check user balances
```bash
sqlite3 banking.db "SELECT username, balance FROM accounts;"
```

### View transfers
```bash
sqlite3 banking.db "SELECT transfer_id, from_user, to_user, amount, status FROM transfers;"
```

### Audit trail
```bash
sqlite3 banking.db "SELECT operation, username, details, timestamp FROM audit_logs;"
```

