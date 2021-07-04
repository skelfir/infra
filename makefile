.PHONY: create destroy preview plan

apply:
	pulumi up --yes

plan:
	pulumi preview --diff

preview:
	pulumi preview

destroy:
	pulumi destroy --yes
