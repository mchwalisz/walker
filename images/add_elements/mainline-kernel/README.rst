===============
Mainline-kernel
===============

Allows to bake mainline kernels into ubuntu images during image preparation.
The header and image packages for the requested kernel version dowloaded from
the Ubuntu mainline kernel PPA and installed automatically.
The key component is a python script, cound in `./bin/`.
Currently, only final releases are supported, tags like `4.15-rc3` will not
work.

Overrides:

 * Specify the kernel versions in the ``DIB_KERNEL_VERSIONS`` environment
   variable. E.g.: ``export DIB_KERNEL_VERSIONS=4.10,4.14.5``
 
