from algosdk import account, mnemonic
from algosdk import transaction

private_key, address = account.generate_account()
print(f"address: {address}")
print(f"private key: {private_key}")
print(f"mnemonic: {mnemonic.from_private_key(private_key)}")


"""
# Create a new algod client, configured to connect to our local sandbox
algod_address = "http://localhost:4001"
algod_token = "a" * 64
algod_client = algod.AlgodClient(algod_token, algod_address)

# Or, if necessary, pass alternate headers

# Create a new client with an alternate api key header
special_algod_client = algod.AlgodClient(
    "", algod_address, headers={"X-API-Key": algod_token}
)


exemple :
address: EMXYXYKQNTIELZMGDQN2LCVS4EGV2A2AHCJHDDTLRNV3TIM56K6HA7UY5I
private key: p0qcVKw+V9oogCkXde0sxTb3k1L438lghJ3/OUp8wKQjL4vhUGzQReWGHBulirLhDV0DQDiScY5ri2u5oZ3yvA==
mnemonic: female illness clean turn purpose custom access civil pepper remind nose hobby unveil pilot secret that bomb bag solution paper nerve business champion absent survey
"""

# source https://github.com/algorand/py-algorand-sdk/blob/examples/examples/account.py#L5-L9