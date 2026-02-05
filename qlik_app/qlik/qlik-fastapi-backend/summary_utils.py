# summary_utils.py
from collections import Counter
import statistics

def generate_vehicle_summary(data):
    summary = {}

    summary["Total Vehicles"] = len(data)
    types = [v["type"] for v in data]
    type_count = Counter(types)
    summary["By Type"] = {"Cars": type_count.get("Car", 0), "Bikes": type_count.get("Bike", 0)}

    fuels = [v["fuel"] for v in data]
    fuel_count = Counter(fuels)
    summary["Fuel Type"] = dict(fuel_count)

    car_prices = [v["price"] for v in data if v["type"] == "Car"]
    bike_prices = [v["price"] for v in data if v["type"] == "Bike"]
    summary["Price (₹)"] = {
        "Highest": max(v["price"] for v in data),
        "Lowest": min(v["price"] for v in data),
        "Avg – Cars": round(statistics.mean(car_prices), 2) if car_prices else 0,
        "Avg – Bikes": round(statistics.mean(bike_prices), 2) if bike_prices else 0,
    }

    car_mileage = [v["mileage"] for v in data if v["type"] == "Car" and v["mileage"] > 0]
    bike_mileage = [v["mileage"] for v in data if v["type"] == "Bike"]
    summary["Mileage"] = {
        "Best": max(v["mileage"] for v in data),
        "Worst": min(v["mileage"] for v in data),
        "Avg – Cars": round(statistics.mean(car_mileage), 2) if car_mileage else 0,
        "Avg – Bikes": round(statistics.mean(bike_mileage), 2) if bike_mileage else 0,
    }

    cities = [v["city"] for v in data]
    city_count = Counter(cities)
    summary["City Spread"] = {"Unique Cities": len(city_count), "Top Cities": city_count.most_common(2)}

    years = [v["year"] for v in data]
    year_count = Counter(years)
    summary["Year Trend"] = dict(year_count)

    return summary
