import useRequest from "./useRequest";
import { apiHost } from "./constants";

const useFetchNumbers = () => {
    const { get } = useRequest()
    const fetchNumbers = (page = 1, perPage=600) => get(`https://${apiHost}/numbers?per_page=${perPage}&page=${page}`, null);
  
    return fetchNumbers;
  };

export default useFetchNumbers;
