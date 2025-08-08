from flask import Flask, request, render_template_string
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
  <title>NC811 Positive Responses</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { font-family: Arial, sans-serif; margin: 10px; padding: 0; background: #f5f5f5; }
    h1 { text-align: center; }
    .ticket { background: white; padding: 15px; margin-bottom: 25px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);}
    table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; font-size: 14px; }
    th { background: #333; color: white; }
    tr.green { background-color: #c8f7c5; }
    tr.yellow { background-color: #fff8c4; }
    tr.red { background-color: #f7c5c5; }
    @media (max-width: 600px) {
      th, td { font-size: 16px; padding: 10px; }
    }
  </style>
</head>
<body>
  <h1>NC811 Positive Responses</h1>
  {% if results %}
    {% for ticket, rows in results.items() %}
      <div class="ticket">
        <h2>Ticket {{ ticket }}</h2>
        {% if rows %}
          <table>
            <thead>
              <tr><th>Member</th><th>Description</th><th>Response</th><th>Op ID</th></tr>
            </thead>
            <tbody>
            {% for row in rows %}
              <tr class="{{ row.color }}">
                <td>{{ row.member }}</td>
                <td>{{ row.description }}</td>
                <td>{{ row.response }}</td>
                <td>{{ row.op_id }}</td>
              </tr>
            {% endfor %}
            </tbody>
          </table>
        {% else %}
          <p>No data found or ticket invalid.</p>
        {% endif %}
      </div>
    {% endfor %}
  {% else %}
    <p>No tickets specified. Use <code>?tickets=123456789,987654321</code> in the URL.</p>
  {% endif %}
</body>
</html>
"""

def determine_color(response_text):
    # Extract codes from response_text if present
    # NC811 response codes are numeric, often shown in the response field
    codes_map = {
        'green': [10, 20],
        'yellow': [55, 60, 80],
        'red': []  # everything else
    }
    # Try to find numbers in response_text (ex: "Code 20 - Marked")
    nums = re.findall(r'\b\d+\b', response_text)
    nums = [int(n) for n in nums]
    for n in nums:
        if n in codes_map['green']:
            return 'green'
        if n in codes_map['yellow']:
            return 'yellow'
    # Default red if no green/yellow codes found
    # Also if response contains “No Conflict” or “Marked” without code, treat green
    text = response_text.lower()
    if 'no conflict' in text or 'marked' in text:
        return 'green'
    return 'red'

def get_ticket_data(ticket_number):
    url = f"https://newtina.nc811.org/newtinweb/responsedisplay.nas?ticket={ticket_number}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
    except Exception:
        return []
    soup = BeautifulSoup(r.text, 'html.parser')
    table = soup.find('table')
    results = []

    if table:
        for row in table.find_all('tr')[1:]:
            cols = [c.get_text(strip=True) for c in row.find_all('td')]
            if len(cols) >= 4:
                member, description, response, op_id = cols[:4]
                color = determine_color(response)
                results.append({
                    "member": member,
                    "description": description,
                    "response": response,
                    "op_id": op_id,
                    "color": color
                })
    return results

@app.route("/")
def index():
    ticket_param = request.args.get("tickets", "")
    ticket_numbers = [t.strip() for t in ticket_param.split(",") if t.strip()]
    results = {}
    for t in ticket_numbers:
        results[t] = get_ticket_data(t)
    return render_template_string(HTML_TEMPLATE, results=results)

if __name__ == "__main__":
    app.run(debug=True)
