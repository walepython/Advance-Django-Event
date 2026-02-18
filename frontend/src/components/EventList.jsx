import React, { useEffect, useState } from "react";

function EventList() {
  const [events, setEvents] = useState([]);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/eventApi/")
      .then((res) => res.json())
      .then((data) => setEvents(data));
  }, []);

  return (
    <div className="event-list" style={{ display: "flex", gap: "20px" }}>
      {events.map((event) => (
        <div
          key={event.event_id}
          style={{
            border: "1px solid #ddd",
            borderRadius: "10px",
            width: "300px",
            padding: "10px",
          }}
        >
          {event.image && (
            <img
              src={`http://127.0.0.1:8000${event.image}`}
              alt={event.title}
              style={{ width: "100%", borderRadius: "10px" }}
            />
          )}
          <h3>{event.title}</h3>
          <p>{event.description}</p>
          <p>
            <b>Starts:</b>{" "}
            {new Date(event.start_time).toLocaleString()}
          </p>
          <button style={{ background: "green", color: "white", padding: "5px 10px", border: "none", borderRadius: "5px" }}>
            View Details
          </button>
        </div>
      ))}
    </div>
  );
}

export default EventList;
