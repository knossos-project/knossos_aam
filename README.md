# KNOSSOS Annotator & Annotation Management

The server-side administration program for [KNOSSOS](https://github.com/knossos-project/knossos) Task Management.

Big image annotation projects that involve multiple annotators can make use of Task Management. As admin you can define projects, assign annotators to them and create project tasks.
Inside KNOSSOS the annotator can login to the server and retrieve open tasks. These tasks typically contain annotation start points from where he can begin his work. The annotator can submit his work in multiple submissions and mark tasks as finished when done.

The web page provides annotators and admins with an overview about the work that has been done, time spent on tasks etc. This will be extended gradually. The admin interface (baseurl + /admin) allows for fine-granular control.

## Setup instructions:

1. Install following dependencies:

    * Python2.7
    * GDAL
    * PostgreSQL

2. Download and extract knossos_aam.

3. Install by running `pip install --user .` in knossos_aam directory.

   This installs the KNOSSOS AAM packages (knossos_aam, knossos_aam_backend, knossos_aam_utils) into your local `site-packages` folder and a `knossos-aam` executable into your local binaries folder.

4. Run `knossos-aam init`

   This starts an interactive prompt for setting up a database including the database schema and super user.


5. After that the server can be run with `knossos-aam runserver`
