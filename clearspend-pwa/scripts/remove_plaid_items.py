"""Remove all Plaid items (bank connections) using client credentials.

Checks both Production and Sandbox environments.
"""

import plaid
from plaid.api import plaid_api
from plaid.model.item_remove_request import ItemRemoveRequest
from plaid.model.item_get_request import ItemGetRequest

CLIENT_ID = "69e46df110446b000de754e7"
PRODUCTION_SECRET = "7c288e28e0e03966399273807f2985"
SANDBOX_SECRET = "ba37698ba137e2d901eb317d412d23"

# Check both environments
for env_name, secret, host in [
    ("Production", PRODUCTION_SECRET, plaid.Environment.Production),
    ("Sandbox", SANDBOX_SECRET, plaid.Environment.Sandbox),
]:
    print(f"\n=== {env_name} ===")
    config = plaid.Configuration(
        host=host,
        api_key={"clientId": CLIENT_ID, "secret": secret},
    )
    client = plaid_api.PlaidApi(plaid.ApiClient(config))

    # There's no "list all items" endpoint in Plaid.
    # If you have access tokens, paste them here:
    tokens = [
        # "access-production-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    ]

    if not tokens:
        print(f"  No access tokens configured for {env_name}.")
        print(f"  Plaid has no 'list all items' API endpoint.")
        print(f"  Items can only be removed if you have the access_token.")
    else:
        for t in tokens:
            try:
                resp = client.item_remove(ItemRemoveRequest(access_token=t))
                print(f"  {t[:25]}... removed (request_id: {resp.request_id})")
            except Exception as e:
                print(f"  {t[:25]}... FAILED: {e}")

print("\n--- Summary ---")
print("Without access_tokens, items cannot be removed via API.")
print("The access_tokens were stored in the old Kivy app on your phone.")
print("\nAlternatives:")
print("  1. Log into your bank's website → Settings → Security → Connected Apps → Revoke Plaid")
print("  2. Plaid auto-expires inactive items after ~90 days")
print("  3. If you still have the old app installed, check its local database for tokens")
