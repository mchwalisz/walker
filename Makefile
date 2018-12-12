help:
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

image-prepare:          ## Create customized OS image
	cd images/preparation/ && ./prepare.py --release xenial --diskimage myimage.tgz --kernel 4.14.5 --kernel 3.18.87 build

image-deployment:       ## Deploy customized OS image on nodes
	cd images/deployment && ansible-playbook deployment.yml

software-deployment:    ## Configure nodes
	cd deployment/ && ansible-playbook main.yml

select-kernel:          ## Select kernel
	cd experiment && ./experiment.py select-kernel

experiment:             ## Execute experiment
	cd experiment && ./experiment.py run

analysis:               ## Data analysis, i.e. start jupyter notebook
	jupyter notebook analysis/Connectivity\ Analysis.ipynb

.PHONY: help image_prepare image_deployment software_deployment experiment_1 experiment_2 analysis
