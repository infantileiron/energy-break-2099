import {request} from "./client";export const fetchReviews=()=>request("/reviews");export const createReviews=(value:unknown)=>request("/reviews","POST",value);
