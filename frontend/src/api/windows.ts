import {request} from "./client";export const fetchWindows=()=>request("/windows");export const createWindows=(value:unknown)=>request("/windows","POST",value);
