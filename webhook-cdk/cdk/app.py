#!/usr/bin/env python3
import aws_cdk as cdk
from webhook_cdk.webhook_stack import ArgoCdWebhookStack


app = cdk.App()

ArgoCdWebhookStack(
    app,
    "ArgoCdWebhookStack",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region"),
    ),
)

app.synth()
