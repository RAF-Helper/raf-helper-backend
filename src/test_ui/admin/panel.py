"""Streamlit admin panel for managing Staff and Events indexes."""

import os
from datetime import datetime
from typing import Optional

import streamlit as st
import httpx

def check_password():
    """Simple Streamlit authentication."""
    def password_entered():
        if st.session_state["password"] == os.getenv("ADMIN_UI_PASSWORD", "admin123"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.error("😕 Password incorrect")
        return False
    else:
        return True

# Configuration
SERVICE_URL = os.getenv("SERVICE_URL", "http://localhost:8000")
API_PREFIX = "/admin"

# Staff endpoints
STAFF_ENDPOINT = f"{SERVICE_URL}{API_PREFIX}/staff"
STAFF_SEARCH_ENDPOINT = f"{STAFF_ENDPOINT}/search"
EVENTS_ENDPOINT = f"{SERVICE_URL}{API_PREFIX}/events"
EVENTS_SEARCH_ENDPOINT = f"{EVENTS_ENDPOINT}/search"


st.set_page_config(
    page_title="RAF Helper Admin",
    page_icon="🔧",
    layout="wide",
)


def staff_tab():
    """Staff management tab."""
    st.header("👥 Staff Management")

    # Add new staff form
    with st.expander("➕ Add New Staff", expanded=False):
        with st.form("add_staff_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("First Name *", help="Staff member's first name")
                surname = st.text_input("Last Name *", help="Staff member's last name")
                fathers_name = st.text_input("Father's Name", help="Patronymic (if applicable)")
                position = st.text_input("Position *", help="Job title/position")
            with col2:
                room = st.text_input("Room *", help="Office room number (e.g., '619a')")
                department = st.text_input("Department *", help="Department/faculty")
                competences = st.text_area("Competences", help="Skills, expertise, subjects taught")
                description = st.text_area("Description", help="Short biography/role description", height=100)

            submitted = st.form_submit_button("➕ Add Staff", type="primary", use_container_width=True)
            if submitted:
                # Validation
                if not all([name, surname, position, room, department]):
                    st.error("❌ Please fill in all required fields (marked with *)")
                else:
                    payload = {
                        "name": name,
                        "surname": surname,
                        "fathers_name": fathers_name or None,
                        "position": position,
                        "room": room,
                        "department": department,
                        "competences": competences or "",
                        "description": description or "",
                    }
                    try:
                        response = httpx.post(STAFF_ENDPOINT + "/", json=payload, timeout=30)
                        if response.status_code == 201:
                            st.success("✅ Staff member added successfully!")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to add staff: {response.text}")
                    except httpx.RequestError as e:
                        st.error(f"❌ Connection error: {str(e)}")

    # Search and filter
    st.subheader("Browse Staff")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        search_name = st.text_input("🔍 Search by name/surname", placeholder="Type to search...", key="staff_search")
    with col2:
        filter_dept = st.text_input("Filter by department", key="staff_dept")
    with col3:
        filter_pos = st.text_input("Filter by position", key="staff_pos")
    with col4:
        filter_room = st.text_input("Filter by room", key="staff_room")

    if st.button("🔄 Refresh", key="refresh_staff"):
        st.rerun()

    # Fetch staff list
    params = {"limit": 100}
    if search_name:
        params["q"] = search_name
    if filter_dept:
        params["department"] = filter_dept
    if filter_pos:
        params["position"] = filter_pos
    if filter_room:
        params["room"] = filter_room

    try:
        response = httpx.get(STAFF_SEARCH_ENDPOINT, params=params, timeout=30)
        if response.status_code != 200:
            st.error(f"Failed to fetch staff: {response.text}")
            return
        staff_list = response.json()
    except httpx.RequestError as e:
        st.error(f"Connection error: {str(e)}")
        return

    if not staff_list:
        st.info("No staff entries found matching your criteria.")
        return

    st.write(f"Found **{len(staff_list)}** staff member(s)")

    # Display staff in expandable cards
    for staff in staff_list:
        with st.expander(f"👤 {staff['name']} {staff['surname']} — {staff['position']}"):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.write(f"**ID:** `{staff['id']}`")
                st.write(f"**Department:** {staff['department']}")
                st.write(f"**Room:** {staff['room']}")
                if staff.get('fathers_name'):
                    st.write(f"**Father's Name:** {staff['fathers_name']}")
                if staff.get('competences'):
                    st.write(f"**Competences:**")
                    st.write(staff['competences'])
                if staff.get('description'):
                    st.write(f"**Description:**")
                    st.write(staff['description'])

            with col2:
                st.write("**Actions:**")
                if st.button("✏️ Edit", key=f"edit_btn_{staff['id']}", use_container_width=True):
                    st.session_state[f"edit_staff_{staff['id']}"] = True
                if st.button("🗑️ Delete", key=f"del_btn_{staff['id']}", use_container_width=True):
                    st.session_state[f"del_staff_{staff['id']}"] = True

            # Edit form
            if st.session_state.get(f"edit_staff_{staff['id']}", False):
                st.markdown("---")
                st.subheader("Edit Staff Member")
                with st.form(f"edit_form_{staff['id']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        edit_name = st.text_input("First Name", value=staff['name'])
                        edit_surname = st.text_input("Last Name", value=staff['surname'])
                        edit_fathers = st.text_input("Father's Name", value=staff.get('fathers_name') or "")
                        edit_position = st.text_input("Position", value=staff['position'])
                    with col2:
                        edit_room = st.text_input("Room", value=staff['room'])
                        edit_dept = st.text_input("Department", value=staff['department'])
                        edit_comp = st.text_area("Competences", value=staff.get('competences') or "")
                        edit_desc = st.text_area("Description", value=staff.get('description') or "")

                    col1, col2 = st.columns(2)
                    with col1:
                        save_btn = st.form_submit_button("💾 Save Changes", type="primary")
                    with col2:
                        cancel_btn = st.form_submit_button("Cancel")

                    if save_btn:
                        payload = {
                            "name": edit_name,
                            "surname": edit_surname,
                            "fathers_name": edit_fathers or None,
                            "position": edit_position,
                            "room": edit_room,
                            "department": edit_dept,
                            "competences": edit_comp,
                            "description": edit_desc,
                        }
                        # Remove None values
                        payload = {k: v for k, v in payload.items() if v is not None and v != ""}
                        try:
                            resp = httpx.patch(f"{STAFF_ENDPOINT}/{staff['id']}", json=payload, timeout=30)
                            if resp.status_code == 200:
                                st.success("✅ Staff member updated successfully!")
                                st.session_state[f"edit_staff_{staff['id']}"] = False
                                st.rerun()
                            else:
                                st.error(f"❌ Update failed: {resp.text}")
                        except httpx.RequestError as e:
                            st.error(f"Connection error: {str(e)}")

                    if cancel_btn:
                        st.session_state[f"edit_staff_{staff['id']}"] = False
                        st.rerun()

            # Delete confirmation
            if st.session_state.get(f"del_staff_{staff['id']}", False):
                st.markdown("---")
                st.warning(f"⚠️ Are you sure you want to delete **{staff['name']} {staff['surname']}**?")
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    if st.button("✅ Yes, delete", key=f"confirm_del_yes_{staff['id']}", type="primary"):
                        try:
                            resp = httpx.delete(f"{STAFF_ENDPOINT}/{staff['id']}", timeout=30)
                            if resp.status_code == 204:
                                st.success("✅ Staff member deleted!")
                                st.session_state[f"del_staff_{staff['id']}"] = False
                                st.rerun()
                            else:
                                st.error(f"❌ Delete failed: {resp.text}")
                        except httpx.RequestError as e:
                            st.error(f"Connection error: {str(e)}")
                with col2:
                    if st.button("❌ No, cancel", key=f"confirm_del_no_{staff['id']}"):
                        st.session_state[f"del_staff_{staff['id']}"] = False
                        st.rerun()


def events_tab():
    """Events management tab."""
    st.header("📅 Events Management")

    # Add new event form
    with st.expander("➕ Add New Event", expanded=False):
        with st.form("add_event_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Event Name *")
                description = st.text_area("Description *", height=100)
                participant_requirements = st.text_area("Participant Requirements", height=80)
            with col2:
                date_from = st.date_input("Start Date *")
                date_to = st.date_input("End Date *")
                col2a, col2b = st.columns(2)
                with col2a:
                    bonus_amount = st.number_input("Bonus Amount", min_value=0, step=1000, help="Optional monetary bonus")
                with col2b:
                    participant_amount = st.number_input("Max Participants", min_value=1, step=1, value=10)

            submitted = st.form_submit_button("➕ Add Event", type="primary", use_container_width=True)
            if submitted:
                if not all([name, date_from, date_to, description]):
                    st.error("❌ Please fill in all required fields (marked with *)")
                elif date_from > date_to:
                    st.error("❌ Start date cannot be after end date")
                else:
                    payload = {
                        "name": name,
                        "date_from": date_from.isoformat(),
                        "date_to": date_to.isoformat(),
                        "description": description,
                        "participant_requirements": participant_requirements or "",
                        "bonus_amount": bonus_amount if bonus_amount > 0 else None,
                        "participant_amount": participant_amount,
                    }
                    try:
                        response = httpx.post(EVENTS_ENDPOINT + "/", json=payload, timeout=30)
                        if response.status_code == 201:
                            st.success("✅ Event added successfully!")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to add event: {response.text}")
                    except httpx.RequestError as e:
                        st.error(f"❌ Connection error: {str(e)}")

    # Search and filter
    st.subheader("Browse Events")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        search_name = st.text_input("🔍 Search by name", placeholder="Type to search...", key="events_search")
    with col2:
        filter_date_from = st.date_input("Filter start date from", key="events_date_from")
    with col3:
        filter_date_to = st.date_input("Filter start date to", key="events_date_to")
    with col4:
        filter_bonus = st.number_input("Min bonus", min_value=0, step=1000, key="events_min_bonus")

    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("🔄 Refresh", key="refresh_events"):
            st.rerun()

    # Fetch events list
    params = {"limit": 100}
    if search_name:
        params["q"] = search_name
    if filter_bonus > 0:
        params["bonus_amount"] = filter_bonus

    # Only add date filters if they're actually set (not None)
    if filter_date_from:
        params["date_from"] = filter_date_from.isoformat()
    if filter_date_to:
        params["date_to"] = filter_date_to.isoformat()

    try:
        response = httpx.get(EVENTS_SEARCH_ENDPOINT, params=params, timeout=30)
        if response.status_code != 200:
            st.error(f"Failed to fetch events: {response.text}")
            return
        events_list = response.json()
    except httpx.RequestError as e:
        st.error(f"Connection error: {str(e)}")
        return

    if not events_list:
        st.info("No events found matching your criteria.")
        return

    st.write(f"Found **{len(events_list)}** event(s)")

    # Display events in expandable cards
    for event in events_list:
        with st.expander(f"📅 {event['name']}"):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.write(f"**ID:** `{event['id']}`")
                st.write(f"**Date:** {event['date_from']} → {event['date_to']}")
                st.write(f"**Participants:** {event.get('participant_amount', 1)}")
                if event.get('bonus_amount'):
                    st.write(f"**Bonus:** {event['bonus_amount']} RUB")
                if event.get('description'):
                    st.write(f"**Description:**")
                    st.write(event['description'])
                if event.get('participant_requirements'):
                    st.write(f"**Requirements:**")
                    st.write(event['participant_requirements'])

            with col2:
                st.write("**Actions:**")
                if st.button("✏️ Edit", key=f"edit_btn_e_{event['id']}", use_container_width=True):
                    st.session_state[f"edit_event_{event['id']}"] = True
                if st.button("🗑️ Delete", key=f"del_btn_e_{event['id']}", use_container_width=True):
                    st.session_state[f"del_event_{event['id']}"] = True

            # Edit form
            if st.session_state.get(f"edit_event_{event['id']}", False):
                st.markdown("---")
                st.subheader("Edit Event")
                with st.form(f"edit_form_e_{event['id']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        edit_name = st.text_input("Event Name", value=event['name'])
                        edit_desc = st.text_area("Description", value=event.get('description') or "")
                        edit_req = st.text_area("Participant Requirements", value=event.get('participant_requirements') or "")
                    with col2:
                        edit_date_from = st.date_input("Start Date", value=datetime.fromisoformat(event['date_from']).date())
                        edit_date_to = st.date_input("End Date", value=datetime.fromisoformat(event['date_to']).date())
                        edit_bonus = st.number_input("Bonus Amount", value=event.get('bonus_amount') or 0, min_value=0, step=1000)
                        edit_ppl = st.number_input("Max Participants", value=event.get('participant_amount', 1), min_value=1, step=1)

                    col1, col2 = st.columns(2)
                    with col1:
                        save_btn = st.form_submit_button("💾 Save Changes", type="primary")
                    with col2:
                        cancel_btn = st.form_submit_button("Cancel")

                    if save_btn:
                        payload = {
                            "name": edit_name,
                            "date_from": edit_date_from.isoformat(),
                            "date_to": edit_date_to.isoformat(),
                            "description": edit_desc,
                            "participant_requirements": edit_req,
                            "bonus_amount": edit_bonus if edit_bonus > 0 else None,
                            "participant_amount": edit_ppl,
                        }
                        payload = {k: v for k, v in payload.items() if v is not None and v != ""}
                        try:
                            resp = httpx.patch(f"{EVENTS_ENDPOINT}/{event['id']}", json=payload, timeout=30)
                            if resp.status_code == 200:
                                st.success("✅ Event updated successfully!")
                                st.session_state[f"edit_event_{event['id']}"] = False
                                st.rerun()
                            else:
                                st.error(f"❌ Update failed: {resp.text}")
                        except httpx.RequestError as e:
                            st.error(f"Connection error: {str(e)}")

                    if cancel_btn:
                        st.session_state[f"edit_event_{event['id']}"] = False
                        st.rerun()

            # Delete confirmation
            if st.session_state.get(f"del_event_{event['id']}", False):
                st.markdown("---")
                st.warning(f"⚠️ Are you sure you want to delete event **'{event['name']}'**?")
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    if st.button("✅ Yes, delete", key=f"confirm_del_e_yes_{event['id']}", type="primary"):
                        try:
                            resp = httpx.delete(f"{EVENTS_ENDPOINT}/{event['id']}", timeout=30)
                            if resp.status_code == 204:
                                st.success("✅ Event deleted!")
                                st.session_state[f"del_event_{event['id']}"] = False
                                st.rerun()
                            else:
                                st.error(f"❌ Delete failed: {resp.text}")
                        except httpx.RequestError as e:
                            st.error(f"Connection error: {str(e)}")
                with col2:
                    if st.button("❌ No, cancel", key=f"confirm_del_e_no_{event['id']}"):
                        st.session_state[f"del_event_{event['id']}"] = False
                        st.rerun()


def main():
    if not check_password():
        st.stop()

    st.title("🔧 RAF Helper — Admin Panel")
    st.markdown("---")
    st.info(f"🌐 Backend API: `{SERVICE_URL}`")

    # Check backend health
    try:
        health_resp = httpx.get(f"{SERVICE_URL}/health/ping", timeout=5)
        if health_resp.status_code == 200:
            st.success("✅ Backend is healthy")
        else:
            st.warning("⚠️ Backend responded with an error")
    except Exception:
        st.error("❌ Cannot connect to backend. Make sure it's running and `SERVICE_URL` is correct.")

    tab1, tab2 = st.tabs(["👥 Staff Management", "📅 Events Management"])

    with tab1:
        staff_tab()

    with tab2:
        events_tab()


if __name__ == "__main__":
    main()
