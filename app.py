from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MongoDB configuration
client = MongoClient("mongodb+srv://iamjayadev445_db_user:7kVXmKX5DgokyaH9@cluster0.hq9ktec.mongodb.net/?appName=Cluster0")
db = client['train_management']

# Admin default credentials
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin@123!'

TICKET_PRICE = 10
# --------------------- ROUTES --------------------- #

@app.route('/')
def index():
    return redirect('/login')

# --------------------- USER REGISTRATION --------------------- #
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if username.lower() == ADMIN_USERNAME.lower():
            flash('Cannot register with the username admin!', 'error')
            return redirect('/register')

        account = db.users.find_one({"username": username})
        if account:
            flash('Username already exists!', 'error')
            return redirect('/register')

        db.users.insert_one({"username": username, "email": email, "password": password})
        flash('Registration successful! Please login.', 'success')
        return redirect('/login')

    return render_template('register.html')


# --------------------- USER LOGIN --------------------- #
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['username'] = username
            session['role'] = 'admin'
            return redirect('/admin')

        account = db.users.find_one({"username": username, "password": password})
        if account:
            session['username'] = account['username']
            session['role'] = 'user'
            return redirect('/user')
        else:
            flash('Invalid username or password', 'error')
            return redirect('/login')

    return render_template('login.html')


# --------------------- LOGOUT --------------------- #
@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    flash('Logged out successfully', 'success')
    return redirect('/login')


# --------------------- ADMIN DASHBOARD --------------------- #
@app.route('/admin')
def admin():
    if 'role' in session and session['role'] == 'admin':
        trains = list(db.trains.find())
        return render_template('admin.html', trains=trains)
    else:
        flash('Access denied', 'error')
        return redirect('/login')


# --------------------- ADD TRAIN --------------------- #
@app.route('/add_train', methods=['GET', 'POST'])
def add_train():
    if 'role' in session and session['role'] == 'admin':
        if request.method == 'POST':
            train_name = request.form['train_name']
            source_station = request.form['source_station']
            destination_station = request.form['destination_station']
            departure_time = request.form['departure_time']
            arrival_time = request.form['arrival_time']
            total_seats = int(request.form['total_seats'])
            status = request.form['status']

            db.trains.insert_one({
                "train_name": train_name,
                "source_station": source_station,
                "destination_station": destination_station,
                "departure_time": departure_time,
                "arrival_time": arrival_time,
                "total_seats": total_seats,
                "available_seats": total_seats,
                "status": status
            })
            flash('Train added successfully', 'success')
            return redirect('/admin')

        return render_template('add_train.html')
    else:
        flash('Access denied', 'error')
        return redirect('/login')


# --------------------- VIEW USER DASHBOARD --------------------- #
@app.route('/user')
def user():
    if 'role' in session and session['role'] == 'user':
        trains = list(db.trains.find({"available_seats": {"$gt": 0}}))
        return render_template('user.html', trains=trains)
    else:
        flash('Access denied', 'error')
        return redirect('/login')


# --------------------- BOOK TICKET --------------------- #
@app.route('/book_ticket/<string:train_id>', methods=['GET', 'POST'])
def book_ticket(train_id):
    if 'role' in session and session['role'] == 'user':
        train = db.trains.find_one({"_id": ObjectId(train_id)})

        if not train:
            flash('Train not found', 'error')
            return redirect('/user')

        if train.get('status') == 'Cancelled':
            flash('Booking not allowed for cancelled trains', 'error')
            return redirect('/user')

        if request.method == 'POST':
            seats = int(request.form['seats'])
            if seats > train.get('available_seats', 0):
                flash('Not enough seats available', 'error')
                return redirect(f'/book_ticket/{train_id}')

            total_amount = seats * TICKET_PRICE
            
            result = db.bookings.insert_one({
                "username": session['username'],
                "train_id": train_id,
                "seats_booked": seats,
                "total_amount": total_amount,
                "status": "Booked"
            })
            booking_id = str(result.inserted_id)

            # Update available seats
            db.trains.update_one(
                {"_id": ObjectId(train_id)},
                {"$inc": {"available_seats": -seats}}
            )
            flash('Booking successful! Proceed to payment.', 'success')
            return redirect(f'/payment/{booking_id}')

        return render_template('book_ticket.html', train=train)
    else:
        flash('Access denied', 'error')
        return redirect('/login')


# --------------------- PAYMENT --------------------- #
@app.route('/payment/<string:booking_id>', methods=['GET', 'POST'])
def payment(booking_id):
    if 'role' in session and session['role'] == 'user':
        booking = db.bookings.find_one({"_id": ObjectId(booking_id), "username": session['username']})

        if not booking:
            flash('Booking not found', 'error')
            return redirect('/user')

        if request.method == 'POST':
            db.bookings.update_one({"_id": ObjectId(booking_id)}, {"$set": {"status": "Paid"}})
            flash('Payment successful!', 'success')
            return redirect(f'/ticket/{booking_id}')

        return render_template('payment.html', booking=booking)
    else:
        flash('Access denied', 'error')
        return redirect('/login')


# --------------------- TICKET --------------------- #
@app.route('/ticket/<string:booking_id>')
def ticket(booking_id):
    if 'role' in session and session['role'] == 'user':
        booking = db.bookings.find_one({"_id": ObjectId(booking_id), "username": session['username']})
        if not booking:
            flash('Booking not found', 'error')
            return redirect('/user')

        train = db.trains.find_one({"_id": ObjectId(booking['train_id'])})

        return render_template('ticket.html', booking=booking, train=train)
    else:
        flash('Access denied', 'error')
        return redirect('/login')


# --------------------- DOWNLOAD TICKET --------------------- #
@app.route('/download_ticket/<string:booking_id>')
def download_ticket(booking_id):
    if 'role' in session and session['role'] == 'user':
        booking = db.bookings.find_one({"_id": ObjectId(booking_id), "username": session['username']})
        if not booking:
            flash('Booking not found', 'error')
            return redirect('/user')

        train = db.trains.find_one({"_id": ObjectId(booking['train_id'])})

        ticket_text = f"""
        -------- Train Ticket --------
        Booking ID: {str(booking['_id'])}
        Username: {booking.get('username', '')}
        Train Name: {train.get('train_name', '')}
        Source: {train.get('source_station', '')}
        Destination: {train.get('destination_station', '')}
        Departure: {train.get('departure_time', '')}
        Arrival: {train.get('arrival_time', '')}
        Seats Booked: {booking.get('seats_booked', '')}
        Total Amount: ₹{booking.get('total_amount', '')}
        Status: {booking.get('status', '')}
        ------------------------------
        """

        # Send as a text file
        return send_file(BytesIO(ticket_text.encode()), as_attachment=True, download_name=f"ticket_{str(booking['_id'])}.txt", mimetype='text/plain')
    else:
        flash('Access denied', 'error')
        return redirect('/login')


# --------------------- VIEW BOOKINGS (ADMIN) --------------------- #
@app.route('/view_bookings')
def view_bookings():
    if 'role' in session and session['role'] == 'admin':
        bookings = list(db.bookings.find())
        return render_template('view_bookings.html', bookings=bookings)
    else:
        flash('Access denied', 'error')
        return redirect('/login')


# --------------------- RUN APP --------------------- #
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
