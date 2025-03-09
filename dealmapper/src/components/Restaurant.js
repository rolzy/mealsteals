import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import Spinner from "react-bootstrap/Spinner";
import { useApi } from "../contexts/ApiProvider";

export default function Restaurant() {
  const { restaurant_id } = useParams();
  const [restaurant, setRestaurant] = useState([]);
  const api = useApi();

  useEffect(() => {
    (async () => {
      const response = await api.get("/restaurants/" + restaurant_id);
      if (response.ok) {
        setRestaurant(response.body);
      } else {
        setRestaurant(null);
      }
    })();
  }, [restaurant_id, api]);

  return (
    <>
      {restaurant === undefined ? (
        <Spinner animation="border" />
      ) : (
        <>
          <h1>{restaurant.name}</h1>
          <br />
          <b>Address:</b> {restaurant.street_address}
          <br />
          <b>URL:</b> {restaurant.url}
          <br />
          <b>Latitude:</b> {restaurant.latitude}
          <br />
          <b>Longitude:</b> {restaurant.longitude}
        </>
      )}
    </>
  );
}
