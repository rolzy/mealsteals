import { useParams } from "react-router-dom";
import Body from "../components/Body";
import Restaurant from "../components/Restaurant";

export default function RestaurantPage() {
  const { restaurant_id } = useParams();

  return (
    <Body sidebar>
      <Restaurant restaurant_id={restaurant_id} />
    </Body>
  );
}
