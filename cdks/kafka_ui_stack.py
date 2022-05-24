from aws_cdk import (
    Stack,
    CfnTag,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_elasticloadbalancingv2 as elbv2,
    aws_route53 as route53
)

from constructs import Construct

from configs import general_config, kafka_ui_config

CDL_KAFKA_UI_CONF = kafka_ui_config.KafkaUIConfig()
CDK_GENERAL_CONF = general_config.GeneralConfig()

with open(CDL_KAFKA_UI_CONF.user_data_shell_path) as f:
    kafka_ui_user_data = f.read()

class CdkKafkaUIStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, environment:str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        kafka_ui_service_name = f'etl-kafka-ui-{environment}'
        kafka_ui_instance_name = f'etl-kafka-ui-instance-{environment}'
        kafka_ui_target_group_name = f'etl-kafka-ui-target-group-{environment}'
        kafka_ui_dns = f'kafka-ui-{environment}.com'
        
        kafka_ui_iam_role = iam.CfnRole(self, f'KafkaUIRole-{environment}',
            path='/',
            managed_policy_arns = [
                'arn:aws:iam::aws:policy/AmazonMSKFullAccess',
                'arn:aws:iam::aws:policy/CloudWatchFullAccess'
            ],
            assume_role_policy_document={
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Sid': '',
                        'Effect': 'Allow',
                        'Principal': {
                            'Service': [
                                'ec2.amazonaws.com'
                            ]
                        },
                        'Action': [
                            'sts:AssumeRole'
                        ]
                    }
                ]
            },
        )
        
        kafka_ui_instance_profile = iam.CfnInstanceProfile(self, f'KafkaUIIamInstanceProfile-{environment}',
            instance_profile_name=kafka_ui_instance_name,
            roles = [kafka_ui_iam_role.ref]
        )
        
        kafka_ui_instance = ec2.CfnInstance(self, f'KafkaUIInstance-{environment}',
            instance_type='t3.small',
            key_name=CDK_GENERAL_CONF.ec2_key_name,
            subnet_id=CDK_GENERAL_CONF.subnet_ids[0],
            security_group_ids=CDK_GENERAL_CONF.security_group,
            image_id=CDL_KAFKA_UI_CONF.ami[environment],
            iam_instance_profile=kafka_ui_instance_profile.ref,
            tags=[
                CfnTag(key='Name',value=kafka_ui_service_name),
                CfnTag(key='Cost',value='infra'),
                CfnTag(key='Environment',value=environment)
            ],
            user_data=kafka_ui_user_data
        )
        
        kafka_ui_target_group = elbv2.CfnTargetGroup(self, f'KafkaUITargetGroup-{environment}',
            name=kafka_ui_target_group_name,
            port=CDL_KAFKA_UI_CONF.service_port,
            protocol='HTTP',
            protocol_version='HTTP1',
            target_type='instance',
            targets=[
                elbv2.CfnTargetGroup.TargetDescriptionProperty(
                    id=kafka_ui_instance.ref,
                    port=CDL_KAFKA_UI_CONF.service_port
                )
            ],
            vpc_id=CDK_GENERAL_CONF.vpc_id,
            target_group_attributes=[
                elbv2.CfnTargetGroup.TargetGroupAttributeProperty(
                    key='load_balancing.algorithm.type',
                    value=CDL_KAFKA_UI_CONF.target_group_lb
                )
            ],
            tags=[
                CfnTag(key='Name',value=kafka_ui_service_name),
                CfnTag(key='Cost',value='infra'),
                CfnTag(key='Environment',value=environment)
            ]
        )
        
        kafka_ui_dns_record = route53.CfnRecordSet(self, f'KafkaUIRecordSet-{environment}',
            hosted_zone_id=CDL_KAFKA_UI_CONF.private_zone_id,
            name=kafka_ui_dns,
            type='A',
            alias_target=route53.CfnRecordSet.AliasTargetProperty(
                dns_name=CDL_KAFKA_UI_CONF.recordset_dns_name,
                hosted_zone_id=CDL_KAFKA_UI_CONF.etl_alb_zone_id,
                evaluate_target_health=False
            ),
        )
        
        kafka_ui_listener_rule = elbv2.CfnListenerRule(self, f'KafkaUIListenerRule-{environment}',
            priority=1,
            listener_arn=CDL_KAFKA_UI_CONF.linstener_arn,
            actions = [
                elbv2.CfnListenerRule.ActionProperty(
                    type='forward',
                    target_group_arn=kafka_ui_target_group.ref
                )
            ],
            conditions = [
                elbv2.CfnListenerRule.RuleConditionProperty(
                    field='host-header',
                    host_header_config = elbv2.CfnListenerRule.HostHeaderConfigProperty(
                        values=[kafka_ui_dns_record.ref]
                    ),
                )
            ]
        )
        
