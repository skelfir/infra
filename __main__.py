import pulumi
from importlib import import_module

stack_name = pulumi.get_stack()

stacks = {
	'local': 'infra.stacks.local',
	'dev': 'infra.stacks.dev',
}


def import_stack(stack_name):
	return import_module(stacks.get(stack_name))


stack = import_stack(stack_name)

for key, value in stack.exports.items():
	pulumi.export(key, value)
