#!/usr/bin/env python3
import os

import aws_cdk as cdk
from cdks.cdk_alb_stack import CdkALBStack
from cdks.cdk_msk_stack import CdkMSKStack
from cdks.cdk_redshift_stack import CdkRedshiftStack
from cdks.cdk_eventbridge_stack import CdkEventBridgeStack

from configs.general_config import GeneralConfig

general_conf = GeneralConfig()

def tagging_func(stack, name, env):    
    cdk.Tags.of(stack).add('Name', name)
    cdk.Tags.of(stack).add('Cost', 'cost')
    cdk.Tags.of(stack).add('Environment', env)

"""
    ls command line: cdk ls --context environment=staging
    synth command line: cdk synth --context environment=staging cdk-sqs-staging
    deploy command line: cdk deploy --context environment=staging cdk-sqs-staging
"""

app = cdk.App()
env = app.node.try_get_context("environment")

if env not in ['develop', 'staging', 'production']:
    raise RuntimeError('The environment value does not match allowed values.')

cdk_msk_stack = CdkMSKStack(
    app, 
    f'cdk-msk-{env}', 
    environment=env,
    synthesizer=cdk.DefaultStackSynthesizer(
        file_assets_bucket_name=general_conf.bootstrap_bucket
    )
)
tagging_func(cdk_msk_stack, name=f'cdk-msk-{env}', env=env)

cdk_redshift_stack = CdkRedshiftStack(
    app, 
    f'cdk-etl-redshift-{env}',
    environment=env,
    synthesizer=cdk.DefaultStackSynthesizer(
        file_assets_bucket_name=general_conf.bootstrap_bucket
    )
)
tagging_func(cdk_redshift_stack, name=f'cdk-redshift-{env}', env=env)

cdk_eventbridge_stack = CdkEventBridgeStack(
    app,
    f'cdk-etl-eventbridge-{env}',
    environment=env,
    synthesizer=cdk.DefaultStackSynthesizer(
        file_assets_bucket_name=general_conf.bootstrap_bucket
    )
)
tagging_func(cdk_eventbridge_stack, name=f'cdk-eventbridge-{env}', env=env)

app.synth()
