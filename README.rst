CInP Python Implementation
==========================

Requirements
------------

Minimum version of django is 1.8 when using the django_orm


Instalation
-----------

Can be installed via pip::

  pip install cinp


debian pacaging files are also included, to build the cinp package::

  dpkg-buildpackage

this should create a .deb file in the parent directory.



File Paramaters/Fields
----------------------

The core toPython returns File Paramaters/Fields as a tuple, the first part being
a readable file handle, the second being the filename the client specified when
uploading the file, or None if it was not specified.  This file handle, depending
on how it was refrenced may be a in memory buffer, a http request, or a file on disk.
Depending on your use case, you may want to make your own tempfile and copy the readable
file handle into that.  You can use the `allowed_scheme_list` to force usage
of a scheme that stores it's temporary file on disk (such as djfh ).

NOTE: DO NOT RELY ON THE FILENAME TO DETERMINE THE TYPE OF THE FILE.
The Filename is specified by the client, and is in no way reliable for much more than
some metadata info.

For the Django ORM, the toPython function wraps the value in a Django File
(django.core.files.File) Object.  For Paramaters, this File object is pointing at
the file handle as from above. For Fields, the storage class that the django field
is using, is used to save the file and return the Field object which is then set
as the value of the field.

For the djfh (django file handler), uploaded files are stored in
cinp.dhango_file_handler.FILE_STORAGE directory and cleaned up by setting a cron to
run the djfhCleaner every 15 min or so. The default is to remove the file after
 it is 2 hours old ( specified by cinp.dhango_file_handler.FILE_TTL ). On Unix
type systems, the open file handle passed in will point to the content of the file,
even after it has deleted, until the file handle has been closed.
