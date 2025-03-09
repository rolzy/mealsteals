import Stack from "react-bootstrap/Stack";
import { Link } from "react-router-dom";
import TimeAgo from "./TimeAgo";

export default function RestaurantOverview({ restaurant }) {
  return (
    <Stack direction="horizontal" gap={3} className="Restaurant">
      <div>
        <p>
          <Link to={`/restaurants/${restaurant.id}`}>{restaurant.name}</Link>
          &nbsp;&mdash;&nbsp;
          {restaurant.street_address}
          <>
            {restaurant.deals_last_updated !== null && (
              <>
                &nbsp;&mdash;&nbsp; Deal last updated{" "}
                <TimeAgo isoDate={restaurant.deals_last_updated} />
              </>
            )}
          </>
        </p>
      </div>
    </Stack>
  );
}
