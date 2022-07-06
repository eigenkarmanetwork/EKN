# Database Automatic Update System

### Version System

We are using the semantic versioning system. See semantic versioning [here](https://semver.org/).

### When to Make a New Database Version

Whenever you make a change to database structure (i.e., a new table, add a column to a table, alter a table or column, etc.), you should make a new version.

### How to Make a New Database Version

The first thing you should do when making a new database version is move the current database to a different location.

Second, update etn.database._create_database to have the new structure you want. Ensure that you change the version value in the INSERT statement.

Third, create a file in database_migration.versions under the name v{MAJOR}_{MINOR}_{PATCH}.py. Ensure that file has a function called update with the type signature Callable[[DatabaseManager], None]. This function calls all the necessary SQL commands to change the current version to your new version. Ensure this function changes the etn_settings table to reflect the new version.

Fourth, update database_migration.update to import the file you created in step three, then add the entry into main_database_versions. The key should be your new version without the v, and then the value should be v{MAJOR}_{MINOR}_{PATCH}.update.

Lastly, start ETN locally and see if the new database is created in the proper structure. Stop the service and delete the created databases, then copy over the file you moved in step one to its original location and start ETN. Ensure the database is updated correctly. If both of these cases worked, you are now able to commit and merge your new version.
