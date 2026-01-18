from __future__ import annotations

import time
import secrets
from decimal import Decimal
from typing import Dict, Any

import Pyro5.api

from common import money, compute_fee, new_id

@Pyro5.api.expose
class BankApplicationServer:
    """
    Phase 1 BAS Server (Application Tier)
    - Holds all state in-memory (NO SQLite in Phase 1).
    - Provides RPC methods for:
      login, balance query, submit transfer, transfer status.
    """

    def __init__(self):
        # Mock users (username -> password)
        self.users = {
            "alice": "alice123",
            "bob": "bob123",
        }

        # Account balances (username -> Decimal balance)
        self.balances = {
            "alice": money("50000.00"),
            "bob": money("1000.00"),
        }

        # Sessions (token -> username)
        self.sessions: Dict[str, str] = {}

        # Transfers (transfer_id -> transfer record dict)
        self.transfers: Dict[str, Dict[str, Any]] = {}

    # ---------- helpers ----------
    def _require_user(self, token: str) -> str:
        user = self.sessions.get(token)
        if not user:
            raise ValueError("401 Unauthorized: invalid/expired token")
        return user

    # ---------- RPC methods ----------
    def login(self, username: str, password: str) -> Dict[str, Any]:
        # mock auth
        if username not in self.users or self.users[username] != password:
            return {"ok": False, "error": "Invalid credentials"}

        token = secrets.token_hex(16)
        self.sessions[token] = username
        return {"ok": True, "token": token}

    def get_balance(self, token: str) -> Dict[str, Any]:
        user = self._require_user(token)
        return {"ok": True, "user": user, "balance": str(self.balances[user])}

    def submit_transfer(self, token: str, recipient: str, amount_str: str, reference: str = "") -> Dict[str, Any]:
        sender = self._require_user(token)

        # Validation
        if recipient not in self.users:
            return {"ok": False, "error": "Invalid recipient account"}
        if recipient == sender:
            return {"ok": False, "error": "Recipient cannot be the sender"}

        try:
            amount = money(amount_str)
        except Exception:
            return {"ok": False, "error": "Invalid amount format"}

        if amount <= money("0.00"):
            return {"ok": False, "error": "Amount must be > 0"}

        fee = compute_fee(amount)
        total = amount + fee

        if self.balances[sender] < total:
            transfer_id = new_id("tr")
            self.transfers[transfer_id] = {
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
            return {"ok": False, "error": "Insufficient funds", "transfer_id": transfer_id}

        # Process synchronously in Phase 1 (simple)
        transfer_id = new_id("tr")
        self.transfers[transfer_id] = {
            "transfer_id": transfer_id,
            "from": sender,
            "to": recipient,
            "amount": str(amount),
            "fee": str(fee),
            "reference": reference,
            "status": "PENDING",
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
        }

        # Apply updates (in-memory "atomic" section)
        self.balances[sender] = money(self.balances[sender] - total)
        self.balances[recipient] = money(self.balances[recipient] + amount)

        self.transfers[transfer_id]["status"] = "COMPLETED"
        self.transfers[transfer_id]["updated_at"] = int(time.time())

        return {
            "ok": True,
            "transfer_id": transfer_id,
            "status": "COMPLETED",
            "fee": str(fee),
            "sender_new_balance": str(self.balances[sender]),
        }

    def get_transfer_status(self, token: str, transfer_id: str) -> Dict[str, Any]:
        _ = self._require_user(token)
        tr = self.transfers.get(transfer_id)
        if not tr:
            return {"ok": False, "error": "Transfer not found"}
        return {"ok": True, "transfer": tr}


def main():
    # Start Pyro daemon + register server object
    daemon = Pyro5.api.Daemon(host="127.0.0.1")  # localhost only for Phase 1
    uri = daemon.register(BankApplicationServer(), objectId="BAS")

    print("BAS server running.")
    print("URI:", uri)
    print("Object name: BAS")
    print("Keep this terminal open.")
    daemon.requestLoop()


if __name__ == "__main__":
    main()
