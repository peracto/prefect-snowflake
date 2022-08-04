"""Credentials class to authenticate Snowflake."""

from typing import Dict, Optional

from prefect.blocks.core import Block
from pydantic import Field, SecretBytes, SecretStr, root_validator
from snowflake import connector


class SnowflakeCredentials(Block):
    """
    Block used to manage authentication with Snowflake.

    Args:
        account: The snowflake account name.
        user: The user name used to authenticate.
        password: The password used to authenticate.
        private_key: The PEM used to authenticate.
        database: The name of the default database to use.
        warehouse: The name of the default warehouse to use.
        authenticator: The type of authenticator to use for initializing
            connection (oauth, externalbrowser, etc); refer to
            [Snowflake documentation](https://docs.snowflake.com/en/user-guide/python-connector-api.html#connect)
            for details, and note that `externalbrowser` will only
            work in an environment where a browser is available.
        token: The OAuth or JWT Token to provide when
            authenticator is set to OAuth.
        schema: The name of the default schema to use.
        role: The name of the default role to use.
        autocommit: Whether to automatically commit.

    Example:
        Load stored Snowflake credentials:
        ```python
        from prefect_snowflake import SnowflakeCredentials
        snowflake_credentials_block = SnowflakeCredentials.load("BLOCK_NAME")
        ```
    """  # noqa E501

    _block_type_name = "Snowflake Credentials"
    _logo_url = "https://images.ctfassets.net/gm98wzqotmnx/2DxzAeTM9eHLDcRQx1FR34/f858a501cdff918d398b39365ec2150f/snowflake.png?h=250"  # noqa

    account: str
    user: str
    password: Optional[SecretStr] = None
    database: Optional[str] = None
    warehouse: Optional[str] = None
    private_key: Optional[SecretBytes] = None
    authenticator: Optional[str] = None
    token: Optional[SecretStr] = None
    schema_: Optional[str] = Field(alias="schema")
    role: Optional[str] = None
    autocommit: Optional[bool] = None

    @root_validator(pre=True)
    def _validate_auth_kwargs(cls, values):
        """
        Ensure an authorization value has been provided by the user.
        """
        auth_params = ("password", "private_key", "authenticator", "token")
        if not any(values.get(param) for param in auth_params):
            auth_str = ", ".join(auth_params)
            raise ValueError(
                f"One of the authentication keys must be provided: {auth_str}\n"
            )
        return values

    def _get_connect_params(
        self, database: Optional[str] = None, warehouse: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Creates a connect params mapping to pass into get_connection.
        """
        connect_params = {
            "account": self.account,
            "user": self.user,
            "password": self.password,
            "database": self.database,
            "warehouse": self.warehouse,
            "private_key": self.private_key,
            "authenticator": self.authenticator,
            "token": self.token,
            "schema": self.schema_,
            "role": self.role,
            "autocommit": self.autocommit,
            # required to track task's usage in the Snowflake Partner Network Portal
            "application": "Prefect_Snowflake_Collection",
        }

        # filter out unset values
        connect_params = {
            param: value for param, value in connect_params.items() if value is not None
        }

        # override specific values
        if database is not None:
            connect_params["database"] = database
        if warehouse is not None:
            connect_params["warehouse"] = warehouse

        for param in ("password", "private_key", "token"):
            if param in connect_params:
                connect_params[param] = connect_params[param].get_secret_value()

        for param in ("database", "warehouse"):
            if param not in connect_params:
                raise ValueError(
                    f"The {param} must be set in either "
                    f"SnowflakeCredentials or the task"
                )

        return connect_params

    def get_connection(
        self, database: Optional[str] = None, warehouse: Optional[str] = None
    ) -> connector.SnowflakeConnection:
        """
        Returns an authenticated connection that can be
        used to query from Snowflake databases.

        Args:
            database: The name of the database to use; overrides
                the class definition if provided.
            warehouse: The name of the warehouse to use; overrides
                the class definition if provided.

        Returns:
            The authenticated SnowflakeConnection.

        Examples:
            ```python
            from prefect import flow
            from prefect_snowflake import SnowflakeCredentials

            @flow
            def snowflake_credentials_flow():
                snowflake_credentials = SnowflakeCredentials(
                    account="account",
                    user="user",
                    password="password",
                    database="database",
                    warehouse="warehouse",
                )
                return snowflake_credentials

            snowflake_credentials_flow()
            ```
        """
        connect_params = self._get_connect_params(
            database=database, warehouse=warehouse
        )
        connection = connector.connect(**connect_params)
        return connection
