import {request} from "./client";export const fetchReports=()=>request("/reports");export const createReports=(value:unknown)=>request("/reports","POST",value);
