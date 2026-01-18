from __future__ import annotations

import time
import secrets
from decimal import Decimal
from typing import Dict, Any, Optional

import Pyro5.api

from common import money, compute_fee, new_id

@Pyro5.api.expose
class BankApplicationServer:
    """
    Phase 2 BAS Server (Application Tier)
    - Communicates with BDB server for persistent storage
    - Handles authentication, business logic, and transfer processing
    - Provides RPC methods for:
      login, balance query, submit transfer, transfer status.
    """

    def __init__(self, bdb_uri: Optional[str] = None):
        """
        Initialize BAS server.
        
        Args:
            bdb_uri: URI to BDB server (e.g., "PYRO:BDB@127.0.0.1:9091")
        """
        # Default BDB URI
        if bdb_uri is None:
            bdb_uri = "PYRO:BDB@127.0.0.1:9091"
        
        # Connect to BDB server
        self.bdb = Pyro5.api.Proxy(bdb_uri)
        
        # Sessions (token -> username) - kept in-memory on BAS
        self.sessions: Dict[str, str] = {}

    # ---------- helpers ----------
    def _require_user(self, token: str) -> str:
        """Verify token and return username."""
        user = self.sessions.get(token)
        if not user:
            raise ValueError("401 Unauthorized: invalid/expired token")
        return user

    # ---------- RPC methods ----------
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate user against BDB and create session."""
        try:
            # Verify credentials with BDB
            if not self.bdb.verify_user(username, password):
                return {"ok": False, "error": "Invalid credentials"}

            # Create session token
            token = secrets.token_hex(16)
            self.sessions[token] = username
            return {"ok": True, "token": token}
        except Exception as e:
            return {"ok": False, "error": f"Login error: {str(e)}"}

    def get_balance(self, token: str) -> Dict[str, Any]:
        """Get account balance from BDB."""
        try:
            user = self._require_user(token)
            balance = self.bdb.get_balance(user)
            if balance is not None:
                return {"ok": True, "user": user, "balance": balance}
            else:
                return {"ok": False, "error": "Account not found"}
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            return {"ok": False, "error": f"Error retrieving balance: {str(e)}"}

    def submit_transfer(self, token: str, recipient: str, amount_str: str, reference: str = "") -> Dict[str, Any]:
        """Submit a transfer request."""
        try:
            sender = self._require_user(token)

            # Validation: Check if recipient exists
            recipient_user = self.bdb.get_user(recipient)
            if not recipient_user:
                return {"ok": False, "error": "Invalid recipient account"}
            
            if recipient == sender:
                return {"ok": False, "error": "Recipient cannot be the sender"}

            try:
                amount = money(amount_str)
            except Exception:
                return {"ok": False, "error": "Invalid amount format"}

            if amount <= money("0.00"):
                return {"ok": False, "error": "Amount must be > 0"}

            # Calculate fee
            fee = compute_fee(amount)
            total = amount + fee

            # Get sender's current balance from BDB
            balance_str = self.bdb.get_balance(sender)
            if balance_str is None:
                return {"ok": False, "error": "Sender account not found"}
            
            sender_balance = money(balance_str)

            # Check for insufficient funds
            if sender_balance < total:
                transfer_id = new_id("tr")
                transfer_record = {
                    "transfer_id": transfer_id,
                    "from": sender,
                    "to": recipient,
                    "amount": str(amount),
                    "fee": str(fee),
                    "reference": reference,
                    "status": "FAILED",
                    "reason": "Insufficient funds",
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
                # Store failed transfer in BDB
                self.bdb.create_transfer(transfer_record)
                return {"ok": False, "error": "Insufficient funds", "transfer_id": transfer_id}

            # Process transfer: Create record, update balances
            transfer_id = new_id("tr")
            transfer_record = {
                "transfer_id": transfer_id,
                "from": sender,
                "to": recipient,
                "amount": str(amount),
                "fee": str(fee),
                "reference": reference,
                "status": "COMPLETED",
                "reason": "",
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
            }

            # Store transfer record in BDB
            if not self.bdb.create_transfer(transfer_record):
                return {"ok": False, "error": "Failed to create transfer record"}

            # Update sender's balance (debit: amount + fee)
            new_sender_balance = sender_balance - total
            if not self.bdb.update_balance(sender, str(new_sender_balance)):
                return {"ok": False, "error": "Failed to update sender balance"}

            # Update recipient's balance (credit: amount only)
            recipient_balance_str = self.bdb.get_balance(recipient)
            if recipient_balance_str is None:
                return {"ok": False, "error": "Recipient account error"}
            
            recipient_balance = money(recipient_balance_str)
            new_recipient_balance = recipient_balance + amount
            if not self.bdb.update_balance(recipient, str(new_recipient_balance)):
                return {"ok": False, "error": "Failed to update recipient balance"}

            return {
                "ok": True,
                "transfer_id": transfer_id,
                "status": "COMPLETED",
                "fee": str(fee),
                "sender_new_balance": str(new_sender_balance),
            }

        except ValueError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            return {"ok": False, "error": f"Transfer error: {str(e)}"}

    def get_transfer_status(self, token: str, transfer_id: str) -> Dict[str, Any]:
        """Get transfer status from BDB."""
        try:
            _ = self._require_user(token)
            transfer = self.bdb.get_transfer(transfer_id)
            if not transfer:
                return {"ok": False, "error": "Transfer not found"}
            return {"ok": True, "transfer": transfer}
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            return {"ok": False, "error": f"Error retrieving transfer: {str(e)}"}


def main():
    """Start BAS daemon + register server object."""
    # Default BDB URI - ensure BDB server is running first!
    bdb_uri = "PYRO:BDB@127.0.0.1:9091"
    
    daemon = Pyro5.api.Daemon(host="127.0.0.1", port=9090)
    uri = daemon.register(BankApplicationServer(bdb_uri), objectId="BAS")

    print("BAS server running.")
    print("URI:", uri)
    print("Object name: BAS")
    print(f"Connected to BDB at: {bdb_uri}")
    print("Keep this terminal open.")
    daemon.requestLoop()


if __name__ == "__main__":
    main()
