import Pyro5.api
from typing import Optional, Dict, Any

BAS_URI = "PYRO:BAS@127.0.0.1:9090"  # We'll override this automatically below

def prompt(msg: str) -> str:
    return input(msg).strip()

def login_menu():
    """Print the login menu."""
    print("\n=== Banking Client (Phase 1) ===")
    print("1) Login")
    print("0) Exit")

def authenticated_menu(username: Optional[str]):
    """Print the authenticated menu."""
    if username is None:
        username = "User"
    print(f"\n=== Banking Client - {username} ===")
    print("1) View Balance")
    print("2) Submit Transfer")
    print("3) Transfer Status Query")
    print("4) Logout")

def main():
    # We use a name server-free approach: connect by direct URI printed by server
    # But Pyro also supports "PYRO:BAS@host:port" when objectId and daemon port match.
    #
    # To avoid confusion, we'll ask you to paste the URI printed by BAS once.

    uri = prompt("Paste BAS URI from server terminal: ")
    bas = Pyro5.api.Proxy(uri)

    token = None
    username: Optional[str] = None

    while True:
        # If not logged in, show login menu
        if not token:
            login_menu()
            choice = prompt("Choose: ")

            if choice == "1":
                # Login
                u = prompt("Username: ")
                p = prompt("Password: ")
                try:
                    res = bas.login(u, p)
                except Exception as e:
                    print("Login RPC error:", e)
                    continue

                # Defensive handling: server should return a dict with {'ok': True, 'token': ...}
                if isinstance(res, dict):
                    if res.get("ok"):
                        token = res["token"]
                        username = u
                        print(f"Login successful. Welcome, {username}!")
                    else:
                        print("Login failed:", res.get("error") or res)
                else:
                    print("Unexpected response from server (not a dict):", type(res), res)

            elif choice == "0":
                print("Goodbye!")
                break
            else:
                print("Invalid option.")

        # If logged in, show authenticated menu
        else:
            authenticated_menu(username)
            choice = prompt("Choose: ")

            if choice == "1":
                # View Balance
                try:
                    res: Optional[Dict[str, Any]] = bas.get_balance(token)
                    if res and res.get("ok"):
                        print(f"Balance for {res.get('user')}: ${res.get('balance')}")
                    else:
                        print("Failed to get balance:", res)
                except Exception as e:
                    print("Error:", e)

            elif choice == "2":
                # Submit Transfer
                try:
                    recipient = prompt("Recipient username: ")
                    amount = prompt("Amount (e.g., 2500.00): ")
                    ref = prompt("Reference (optional): ")
                    res: Optional[Dict[str, Any]] = bas.submit_transfer(token, recipient, amount, ref)
                    if res and res.get("ok"):
                        print(f"Transfer successful!")
                        print(f"  Transfer ID: {res.get('transfer_id')}")
                        print(f"  Status: {res.get('status')}")
                        print(f"  Fee: ${res.get('fee')}")
                        print(f"  New balance: ${res.get('sender_new_balance')}")
                    else:
                        print(f"Transfer failed: {res.get('error') if res else 'Unknown error'}")
                        if res and res.get('transfer_id'):
                            print(f"  Transfer ID (for tracking): {res.get('transfer_id')}")
                except Exception as e:
                    print("Error:", e)

            elif choice == "3":
                # Transfer Status Query
                try:
                    tid = prompt("Transfer ID: ")
                    res: Optional[Dict[str, Any]] = bas.get_transfer_status(token, tid)
                    if res and res.get("ok"):
                        tr = res.get("transfer")
                        print(f"Transfer Details:")
                        print(f"  ID: {tr.get('transfer_id')}")
                        print(f"  From: {tr.get('from')}")
                        print(f"  To: {tr.get('to')}")
                        print(f"  Amount: ${tr.get('amount')}")
                        print(f"  Fee: ${tr.get('fee')}")
                        print(f"  Status: {tr.get('status')}")
                        if tr.get('reason'):
                            print(f"  Reason: {tr.get('reason')}")
                        if tr.get('reference'):
                            print(f"  Reference: {tr.get('reference')}")
                    else:
                        print("Transfer not found:", res.get('error') if res else 'Unknown error')
                except Exception as e:
                    print("Error:", e)

            elif choice == "4":
                # Logout
                token = None
                username = None
                print("Logged out successfully. Returning to login menu.")

            else:
                print("Invalid option.")

if __name__ == "__main__":
    main()
