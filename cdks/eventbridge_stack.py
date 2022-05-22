from aws_cdk import Stack
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk.aws_lambda import Function
from aws_cdk import aws_lambda as lambda_
from constructs import Construct

'''
EventBridge stack for monitoring Redshift data change status whether is failure or aborted.
The Lambda function (etl_data_monitoring_alert_<env>) target need to be built before deploy this stack
'''

class CdkEventBridgeStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, environment: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        rule_name = f"redshift_slack_alert_{environment}"
        lambda_fn_name = f'lambda_redshift_slack_alert_{environment}'
                        
        rule = events.Rule(self, rule_name,
            event_pattern=events.EventPattern(
                source=["aws.redshift-data"],
                detail_type=["Redshift Data Statement Status Change"],
                detail={"state": 
                    [{"anything-but": 
                        ["FINISHED", "COMPLETED"]}]
                }
            )
        )
        
        rule.add_target(targets.LambdaFunction(
            Function.from_function_name(
                self, 
                id=f'{lambda_fn_name}_eb_target', 
                function_name=lambda_fn_name),
            retry_attempts=2
            )
        )
        
        lambda_.CfnPermission(
            self, "eventbridge_lambda_invoke_permission",
            action="lambda:InvokeFunction",
            function_name=lambda_fn_name,
            principal="events.amazonaws.com",
            source_arn=rule.rule_arn
        )
    
