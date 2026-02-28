import axios  from "axios";

export default axios.create({
    baseURL: "https://api.rawg.io/api",
    params:{
        key: "4c94780d7f91403395d297a159192f78"
    }
})