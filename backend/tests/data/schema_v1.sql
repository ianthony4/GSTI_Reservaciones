-- Esquema real de la BD v1.0 (extraido de la BD de la demo de la Fase 3)
CREATE TABLE restaurants (
	id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	address VARCHAR(200) NOT NULL, 
	phone VARCHAR(20) NOT NULL, 
	opening_time TIME NOT NULL, 
	closing_time TIME NOT NULL, 
	PRIMARY KEY (id)
);
CREATE TABLE customers (
	id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	email VARCHAR(120) NOT NULL, 
	phone VARCHAR(20) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
CREATE UNIQUE INDEX ix_customers_email ON customers (email);
CREATE TABLE tables (
	id INTEGER NOT NULL, 
	restaurant_id INTEGER NOT NULL, 
	number INTEGER NOT NULL, 
	capacity INTEGER NOT NULL, 
	location VARCHAR(50) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(restaurant_id) REFERENCES restaurants (id)
);
CREATE TABLE reservations (
	id INTEGER NOT NULL, 
	code VARCHAR(8) NOT NULL, 
	customer_id INTEGER NOT NULL, 
	restaurant_id INTEGER NOT NULL, 
	table_id INTEGER NOT NULL, 
	date DATE NOT NULL, 
	start_time TIME NOT NULL, 
	end_time TIME NOT NULL, 
	party_size INTEGER NOT NULL, 
	status VARCHAR(9) NOT NULL, 
	notes TEXT NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(customer_id) REFERENCES customers (id), 
	FOREIGN KEY(restaurant_id) REFERENCES restaurants (id), 
	FOREIGN KEY(table_id) REFERENCES tables (id)
);
CREATE UNIQUE INDEX ix_reservations_code ON reservations (code);
CREATE TABLE notifications (
	id INTEGER NOT NULL, 
	reservation_id INTEGER NOT NULL, 
	customer_id INTEGER NOT NULL, 
	type VARCHAR(12) NOT NULL, 
	channel VARCHAR(20) NOT NULL, 
	recipient VARCHAR(120) NOT NULL, 
	subject VARCHAR(200) NOT NULL, 
	message TEXT NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	sent_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(reservation_id) REFERENCES reservations (id), 
	FOREIGN KEY(customer_id) REFERENCES customers (id)
);
