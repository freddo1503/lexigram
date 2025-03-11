import aws_cdk as cdk
from helpers import get_account_and_region
from lexigram_stack import Lexigram

account_and_region = get_account_and_region()

app = cdk.App()
Lexigram(
    app,
    "Lexigram",
    env=cdk.Environment(
        account=account_and_region["account"],
        region=account_and_region["region"],
    ),
)

app.synth()
