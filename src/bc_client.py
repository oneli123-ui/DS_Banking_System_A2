import Pyro5.api

BAS_URI = "PYRO:BAS@127.0.0.1:9090"  # We'll override this automatically below

def prompt(msg: str) -> str:
    return input(msg).strip()

def menu(logged_in: bool = False):
    """Print the menu. If logged_in is True, hide the Login option."""
    print("\n=== Banking Client (Phase 1) ===")
    if not logged_in:
        print("1) Login")
    print("2) View Balance")
    print("3) Submit Transfer")
    print("4) Transfer Status Query")
    print("0) Exit")

def main():
    # We use a name server-free approach: connect by direct URI printed by server
    # But Pyro also supports "PYRO:BAS@host:port" when objectId and daemon port match.
    #
    # To avoid confusion, we'll ask you to paste the URI printed by BAS once.

    uri = prompt("Paste BAS URI from server terminal: ")
    bas = Pyro5.api.Proxy(uri)

    token = None

    while True:
        menu(token is not None)
        choice = prompt("Choose: ")

        if choice == "1":
            # Prevent re-login while already authenticated
            if token:
                print("You are already logged in.")
                continue

            u = prompt("Username: ")
            p = prompt("Password: ")
            try:
                res = bas.login(u, p)
            except Exception as e:
                print("Login RPC error:", e)
                continue

            # show debug info
            print("RAW RESPONSE:", res)
            print("TYPE:", type(res))

            # Defensive handling: server should return a dict with {'ok': True, 'token': ...}
            if isinstance(res, dict):
                if res.get("ok"):
                    token = res["token"]
                    print("Login successful.")
                else:
                    print("Login failed:", res.get("error") or res)
            else:
                print("Unexpected response from server (not a dict):", type(res), res)
        elif choice == "2":
            if not token:
                print("You must login first.")
                continue
            print(bas.get_balance(token))

        elif choice == "3":
            if not token:
                print("You must login first.")
                continue
            recipient = prompt("Recipient username: ")
            amount = prompt("Amount (e.g., 2500.00): ")
            ref = prompt("Reference (optional): ")
            print(bas.submit_transfer(token, recipient, amount, ref))

        elif choice == "4":
            if not token:
                print("You must login first.")
                continue
            tid = prompt("Transfer ID: ")
            print(bas.get_transfer_status(token, tid))

        elif choice == "0":
            print("Bye.")
            break

        else:
            print("Invalid option.")

if __name__ == "__main__":
    main()
