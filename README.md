# EigenKarma Network (EKN)

Trust is powerful. Knowing who is capable, value aligned, or has done good work in the past is extremely valuable for all sorts of decisions, but currently it takes lots of effort to collect this information. Imagine if you could leverage your trust network's collective knowledge to get a read of hundreds or thousands of times as many people, with minimal effort!

That is what EigenTrust Network is creating. We use an algorithm similar to Google's PageRank to model trust propagation, setting the subjective source of all trust to each individual. So that from your personal view of the network you can see how much of your trust has flowed to anyone else.

This specific repository is for the EKN API. You can view `app.py` to see all the routes which exist in `etn/routes/`.

## Setup

### Install all requirements:
#### Pip

* (Optional) create a virtualenv. Make sure that it is Python >= 3.10
* `pip install -r requirements.txt`

#### Conda

The following should create a new environment with the appropriate libraries installed:

    conda create --name EKN --file requirements.txt

### Run EKN

There are shell specific scripts to run the service, e.g. in the case of bourne shells, run

    ./start.sh

### Generate data

If you want to prepopulate your database with services, users and votes, use the following:

    ./scripts/generate_network.py

This will create a load of services called `service_<number>` and users called `user_<number>`.
Each service will have a random sample of the available users registered with them, called
`service_<number>_user_<number>`. These server specific users will grant each other a random
number of votes.
All sample users use the same password: `hunter2`

## How to Use

If you're wanting to use the EKN as a regular user, you may want to go to [our website](https://www.eigenkarma.net) where you can sign up and begin trusting people!

If you're a service provider, or wanting to use the API directly, you've come to the right place!

### API Documentation

All our API routes accept both JSON and Standard POST syntax. Our base URL is `https://eigenkarma.net:31415`, for example our register user route is `https://eigenkarma.net:31415/register_user`

#### Registration Routes

These are all our API Routes that have to do with registering something.

##### Register User

URL: `/register_user`

Method: `POST`

Data:

    {
        "username": str,
        "password": str
    }

Returns:

* 409: Username is not available.
* 409: Invalid Username.
* 200: Registration Successful.

Description:

Register a new user with the EKN, `username` and `password` must be passed in plain text.  `username` is case sensitive and must not contain a colon (`:`).

##### Register Temp User

URL: `/register_temp_user`

Method: `POST`

Data:

    {
        "service_user": str,
        "service_name": str,
        "service_key": str
    }

Returns:

* 403: Service name or key is incorrect.
* 409: Username is not available.
* 200: Registration Successful.

Description:

Register a new temporary user with the EKN, `service_user` should be the username on the service you're registering a temp account for.  `service_user` is case sensitive.  Services must get permission from users before sending data off to EKN.  This permission may be through ToS or otherwise.

##### Register Service

URL: `/register_service`

Method: `POST`

Data:

    {
        "name": str
    }

Returns:

* 409: Name is not available.
* 200: service_key: str

Description:

Register a new service with the EKN. `name` is case sensitive.  This will allow you to send votes on behalf of the users in your service.  Calling this function return's your service's EKN key.  For future requests, `name` should be passed as `service_name` and the string returned by this API call should be passed as `service_key`.

##### Register Connection

URL: `/register_connection`

Method: `POST`

Data:

    {
        "service_name": str
        "service_key": str
        "service_user": str (Username on Service)
        "username": str (Username on EKN)
        "password": str (Password on EKN)
        "password_type": Optional[Literal["raw_password", "password_hash", "connection_key", "session_key"]]
    }

Returns

* 403: Service name or key is incorrect.
* 403: Username or Password is incorrect.
* 409: Service user already connected to the EKN.
* 200: JSON:
        {
            "password": str
            "password_type": Literal["password_hash", "conneciton_key", "session_key"]
            "expires": int (unix timestamp or 0 if N/A)
        }

Description:

Connects a user on a service to their user on EKN. `password_type` is optional, and defaults to `"raw_password"`.  This API call returns a JSON string that contains a key to authorize trust votes on behalf of the user.  However, if the user does not authorize services to vote on behalf of them, then a password hash is returned.  This feature is deprecated.  If a connection key is returned, then the user authorizes the service to cast votes on their behalf.  If a session key is returned, then the user authories the service to cast votes on their behalf so long as they've logged into EKN within the last 24 hours. If a session key is returned, then the expires field will contain a unix timestamp of how long the session key is good for.  To get a new session key, please call `/get_current_key`.

#### User Functions

There are a few different user function API calls but most should only be used by [our website](https://www.eigenkarma.net/).

##### Verify Credentials

URL: `/get_current_key`

Method: `POST`

Data:

    {
        "service_name": str
        "service_key": str
        "username": str (Username on Service)
    }

Returns

* 403: Service name or key is incorrect.
* 404: Service is not connected.
* 404: No key available.
* 200: JSON:
        {
            "password": str
            "password_type": Literal["conneciton_key", "session_key"]
            "expires": int (unix timestamp or 0 if N/A)
        }

Description:

Allows a service to get a connection key or session key of a connected user. `username` should be the username or your service, and is case sensitive.

#### Vote Functions

##### Cast Trust Vote

URL: `/vote`

Method: `POST`

Data:

    {
        "service_name": str
        "service_key": str
        "to": str (Username on Service)
        "from": str (Username on Service)
        "password": str (For `from` User)
        "password_type": Optional[Literal["raw_password", "password_hash", "connection_key", "session_key"]]
        "flavor": Optional[str]
        "amount": Optional[int]
    }

Returns

* 400: User cannot vote for themselves.
* 400: Cannot have a negative amount of trust.
* 403: Username or Password is incorrect.
* 403: Service name or key is incorrect.
* 404: 'to' is not connected to this service.
* 404: Flavor does not exist.
* 200: Success.

Description:

Allows a service to vote on behalf of a user. `passwword_type` is optional and defaults to `"raw_password"`. `flavor` is optional and defaults to `"general"`. `amount` is optional and defaults to `1`.

##### Get Trust Vote Count

URL: `/get_vote_count`

Method: `POST`

Data:

    {
        "service_name": str
        "service_key": str
        "for": str (Username on Service)
        "from": str (Username on Service)
        "password": str (For `from` User)
        "password_type": Optional[Literal["raw_password", "password_hash", "connection_key", "session_key"]]
        "flavor": Optional[str]
    }

Returns

* 400: User cannot view themselves.
* 403: Username or Password is incorrect.
* 403: Service name or key is incorrect.
* 404: 'for' is not connected to this service.
* 404: Flavor does not exist.
* 200: JSON:
        {
            "for": str (Username Provided)
            "from": str (Username Provided)
            "votes": int
            "flavor": str
        }

Description:

Allows a service to get the number of times a user (A) has been trusted by user (B) on behalf of a user (B). `passwword_type` is optional and defaults to `"raw_password"`.

If `flavor` is not specified, it will return the total number of times a user (B) has voted for a user (A) in *all* categories.

##### Get Trust Score

URL: `/get_score`

Method: `POST`

Data:

    {
        "service_name": str
        "service_key": str
        "for": str (Username on Service)
        "from": str (Username on Service)
        "password": str (For `from` User)
        "password_type": Optional[Literal["raw_password", "password_hash", "connection_key", "session_key"]]
        "flavor": Optional[str]
    }

Returns

* 400: User cannot view themselves.
* 403: Username or Password is incorrect.
* 403: Service name or key is incorrect.
* 404: 'for' is not connected to this service.
* 404: Flavor does not exist.
* 200: JSON:
        {
            "for": str (Username Provided)
            "from": str (Username Provided)
            "score": float
            "flavor": str
        }

Description:

Allows a service to get the trust score for a user on behalf of, and from the perspective of another user. `passwword_type` is optional and defaults to `"raw_password"`. `flavor` is optional and defaults to `"general"`.

##### Get Trust Categories

URL: `/categories`

Method: `GET`

Returns

* 200: JSON: list[str]

Description:

Returns a JSON list of all the flavors available.

#### Misc Functions

##### Get Total Users

URL: `/get_total_users`

Method: `GET`

Returns

* 200: int

Description:

Returns the total users recorded in EKN, including temporary and real/registered users.

##### Get Total Registered Users

URL: `/get_total_real_users`

Method: `GET`

Returns

* 200: int

Description:

Returns the total users recorded in EKN, excluding temp users.

##### Get Total Temporary Users

URL: `/get_total_temp_users`

Method: `GET`

Returns

* 200: int

Description:

Returns the total users recorded in EKN, excluding real/registered users.

##### Get Total Votes

URL: `/get_total_votes`

Method: `GET`

Returns

* 200: int

Description:

Returns the total number of votes recorded in EKN.
