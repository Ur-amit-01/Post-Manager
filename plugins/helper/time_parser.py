def parse_time(time_str):
    """
    Parse human-readable time string into seconds
    Supports formats like: 1h30m, 2 hours 15 mins, 1day, 30sec, etc.
    """
    time_units = {
        's': 1,
        'sec': 1,
        'second': 1,
        'seconds': 1,
        'm': 60,
        'min': 60,
        'mins': 60,
        'minute': 60,
        'minutes': 60,
        'h': 3600,
        'hour': 3600,
        'hours': 3600,
        'd': 86400,
        'day': 86400,
        'days': 86400
    }

    total_seconds = 0
    current_num = ''
    
    for char in time_str:
        if char.isdigit():
            current_num += char
        else:
            if current_num:
                # Find matching unit
                num = int(current_num)
                unit = char.lower()
                remaining_str = time_str[time_str.index(char):].lower()
                
                # Check for multi-character units
                matched = False
                for unit_str, multiplier in sorted(time_units.items(), key=lambda x: -len(x[0])):
                    if remaining_str.startswith(unit_str):
                        total_seconds += num * multiplier
                        current_num = ''
                        matched = True
                        break
                
                if not matched:
                    raise ValueError(f"Invalid time unit: {char}")
            current_num = ''
    
    if current_num:  # If only number was provided (like "60")
        total_seconds += int(current_num)  # Default to seconds
    
    if total_seconds == 0:
        raise ValueError("No valid time duration found")
    
    return total_seconds



def format_time(seconds):
    """Convert seconds to human-readable time"""
    periods = [
        ('day', 86400),
        ('hour', 3600),
        ('minute', 60),
        ('second', 1)
    ]
    
    result = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            if period_value > 0:
                result.append(f"{period_value} {period_name}{'s' if period_value != 1 else ''}")
    
    return ' '.join(result) if result else "0 seconds"
  
