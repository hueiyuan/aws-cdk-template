from aws_cdk import (
    Stack,
)
from aws_cdk import CfnTag
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from constructs import Construct

class CdkALBStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        """
            alb
        """
        
        etl_alb = elbv2.CfnLoadBalancer(self, "ETLLoadBalancer",
            name='etl',
            type='application',
            ip_address_type='ipv4',
            scheme='internal',
            security_groups = [
                'sg-xxxxx'
            ],
            subnets = [
                'subnet-xxxxx',
            ],
            tags=[
                CfnTag(key='Name',value='alb_name'),
                CfnTag(key='Cost',value='infra')
            ]
        )
        
        default_listener = elbv2.CfnListener(self, "DefaultListener",
            default_actions = [
                elbv2.CfnListener.ActionProperty(
                    type = 'fixed-response',
                    fixed_response_config = elbv2.CfnListener.FixedResponseConfigProperty(
                        status_code='404',
                        content_type='text/plain'
                    ),
                )
            ],
            load_balancer_arn = etl_alb,
            port = 80,
            protocol = 'HTTP'
        )
        
        schema_registry_listener = elbv2.CfnListener(self, "SchemaRegistryListener",
            default_actions = [
                elbv2.CfnListener.ActionProperty(
                    type = 'fixed-response',
                    fixed_response_config = elbv2.CfnListener.FixedResponseConfigProperty(
                        status_code='404',
                        content_type='text/plain'
                    ),
                )
            ],
            load_balancer_arn = etl_alb,
            port = 8080,
            protocol = 'HTTP'
        )
        
