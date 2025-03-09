import React, { useState, useEffect } from "react";
import Spinner from "react-bootstrap/Spinner";
import { useApi } from "../contexts/ApiProvider";
import RestaurantOverview from "./RestaurantOverview";

export default function Restaurants() {
  const [restaurants, setRestaurants] = useState([]);
  const api = useApi();

  useEffect(() => {
    (async () => {
      const response = await api.get("/restaurants", { per_page: 70 });
      if (response.ok) {
        setRestaurants(response.body.items);
      } else {
        setRestaurants(null);
      }
    })();
  }, [api]);

  return (
    <>
      {restaurants === undefined ? (
        <Spinner animation="border" />
      ) : (
        <>
          {restaurants === null ? (
            <p>Could not retrieve restaurants.</p>
          ) : (
            restaurants.map((restaurant) => (
              <RestaurantOverview key={restaurant.id} restaurant={restaurant} />
            ))
          )}
        </>
      )}
    </>
  );
}
