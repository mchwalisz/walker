======
ubuntu
======

Use Ubuntu cloud images as the baseline for built disk images. This element
is widely based on the stock `ubuntu` element, but uses the squashfs-packaged
cloud images provided by ubuntu. This allows to build diskimages based on more
recent Ubuntu, which is no longer distributed as rootfs tarball since xenial.

Overrides:

 * To use a non-default URL for downloading base Ubuntu cloud images,
   use the environment variable ``DIB_CLOUD_IMAGES``
 * To download a non-default release of Ubuntu cloud images, use the
   environment variable ``DIB_RELEASE``. This element will export the
   ``DIB_RELEASE`` variable.

.. element_deps::
