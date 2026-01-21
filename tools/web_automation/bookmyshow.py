from tools.web_automation.browser import Browser


def open_bookmyshow():
    browser = Browser()
    browser.open("https://in.bookmyshow.com")
    return "BookMyShow opened in browser."


def start_booking(movie, city, date_pref, time_pref):
    browser = Browser()
    browser.open("https://in.bookmyshow.com")

    # For now just demonstrate flow
    return (
        "Booking started in browser:\n"
        f"Movie: {movie}\n"
        f"City: {city}\n"
        f"Date: {date_pref}\n"
        f"Time: {time_pref}\n\n"
        "Automation will stop before payment."
    )
