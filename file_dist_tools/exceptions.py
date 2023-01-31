class InvalidFieldValueException(Exception):
    def __init__(self, file_name, field_name, field_value, message=""):
        self.file_name = file_name
        self.field_name = field_name
        self.field_value = field_value
        self.message = f"Invalid field \"{field_name}\", value={field_value}, fileName={file_name}, {message}"
        super().__init__(self.message)


class UnrecognizedFieldException(Exception):
    def __init__(self, field_name, message="Unrecognized field"):
        self.field_name = field_name
        self.message = f"{message} \"{field_name}\""
        super().__init__(self.message)


class InvalidConfigurationException(Exception):
    def __init__(self, file_name, message=""):
        self.file_name = file_name
        self.message = f"Invalid configuration on \"{file_name}\", {message}"
        super().__init__(self.message)
