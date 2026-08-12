def log(log_type,log_message):
    if log_type == 0:
        log_message = "[INFO] " + log_message
    if log_type == 1:
        log_message = "[WARNING] " + log_message
    if log_type == 2:
        log_message = "[ERROR] " + log_message
    if log_type == 3:
        log_message = "[DEBUG] " + log_message
    if log_type == 4:
        log_message = "[UI] " + log_message
    if log_type == 5:
        log_message = "[PLUGIN API] " + log_message
    print(log_message)
