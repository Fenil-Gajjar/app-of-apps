from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_apigatewayv2 as apigw,
    aws_apigatewayv2_integrations as integrations,
    aws_sqs as sqs,
    aws_iam as iam,
)
from constructs import Construct


class ArgoCdWebhookStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # 1️⃣ SQS Queue
        queue = sqs.Queue(
            self,
            "ArgoCdWebhookQueue",
            queue_name="argocd-webhook-queue",
            retention_period=Duration.days(4),
            visibility_timeout=Duration.seconds(60),
        )

        # 2️⃣ Lambda Function
        webhook_lambda = _lambda.Function(
            self,
            "WebhookHandler",
            runtime=_lambda.Runtime.PYTHON_3_10,
            handler="webhook_handler.lambda_handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.seconds(10),
            environment={
                "SQS_QUEUE_URL": queue.queue_url,
                # DO NOT hardcode in real prod – use Secrets Manager later
                "WEBHOOK_SECRET": "argocd-webhook-secret-9f83kdf93kdf",
            },
        )

        # 3️⃣ Allow Lambda to send messages to SQS
        queue.grant_send_messages(webhook_lambda)

        # 4️⃣ API Gateway HTTP API
        http_api = apigw.HttpApi(
            self,
            "ArgoCdWebhookApi",
            api_name="argocd-webhook-api",
        )

        # 5️⃣ Integration
        integration = integrations.HttpLambdaIntegration(
            "WebhookIntegration",
            webhook_lambda,
        )

        # 6️⃣ Route
        http_api.add_routes(
            path="/webhook",
            methods=[apigw.HttpMethod.POST],
            integration=integration,
        )

        # 7️⃣ Output URL (important for Argo CD config)
        self.api_url = http_api.api_endpoint
