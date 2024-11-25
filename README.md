# README: Running and Testing the Django Server

## Prerequisites

Ensure you have the following software installed on your system:
- Python 3.8 or above
- Pip (Python package manager)
- Virtualenv (optional but recommended)

## Setup Instructions

1. **Clone the Repository**
git clone <repository_url>
cd <repository_name>

2. **Creating a Virtual Environment**
python3 -m venv venv
source venv/bin/activate

3. **pip install requirements**
pip install -r requirements.txt

4. **Setup db and create admin user**
python manage.py migrate
python manage.py createsuperuser

5. **Run server**
python manage.py runserver


## Limits:
Given the time constraints, this project was left mostly a flat structure and simple.  In a more robust project, there would be more time spent on organizing files, more robust error handling, appropriate post actions, and general work making the code more maintainable.