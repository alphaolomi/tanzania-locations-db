# Tanzania Locations Repo

## Quick Introduction

Tanzania locations, All Regions from Tanzania, with their respective Districts wards & streets.

Very useful for easily implementing Tanzania locations in any application.

### How to use

What you need before running the code.

1. Install & Start MySQL 8+ Service

2. Extract everything

- Give setup.sh execute permission with `chmod +x ./setup.sh`.

- Run the setup file with `./setup.sh`.

- Close PL/PgSQL prompts with `:q` whenever prompted, this will happen in the last phrase of data extraction, which you
    will need to close the prompt for it to continue eg. "save_regions" etc..

3. This will create a database called `locations` (user `locations`) and load all data.

4. You can check the data with `mysql -u locations -p locations` and run `SELECT * FROM regions;` to verify
   the data is present.

## For Docker

1. Create a .env file based on the provided template:

```bash
cp env.example .env
```

2. Run with Docker Compose (Recommended)

```bash
docker-compose up -d
```

3. Environment variables

```ini
MYSQL_DATABASE=locations
MYSQL_USER=locations
MYSQL_PASSWORD=locations_password
MYSQL_ROOT_PASSWORD=password
MYSQL_HOST_PORT=3306
```

### Credits

A few folks made this happen, from standardizing the data to creating the
database, writing the scripts and testing. Thank you all for your
contributions.

1. Natali Isuja
2. Joe Master
3. Robert Mnama
4. [Ano Rebel](https://github.com/AnoRebel/)
5. [Zacharia23](https://github.com/Zacharia23)
