.PHONY: create destroy preview plan

apply:
	pulumi up --yes --skip-preview

plan:
	pulumi preview --diff

preview:
	pulumi preview

destroy:
	pulumi destroy --yes --skip-preview
