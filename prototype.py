import streamlit as st
import os
from groq import Groq

GROQ_API_KEY = "api_key"  
client = Groq(api_key=GROQ_API_KEY)

def generate_story(user_input):
    # Make the API call
    chat_completion = client.chat.completions.create(
        messages=[{
                    "role": "system",
                    "content": (
                        " You are a professional mutual fund sales repesentative with expertise in writing compelling scripts for negotiation and dela recommendation."
                        "respond the user with a great narrative he cann build with the customer"
                        "also provide him what could be the future in that mutual fund and etc"
                    )
                },
                {
                    "role": "user", 
                    "content": user_input
                }
                ],
        model="llama3-8b-8192",
    )
    
    # Return the response content
    return chat_completion.choices[0].message.content

# Streamlit app interface
st.title('query asker')
st.write('Hello sales rep,Enter your query :')

# User input for story content
user_input = st.text_area("Prompt:", "")

if st.button('Here is what you can create'):
    if user_input:
        # Generate the story based on the user's input
        response = generate_story(user_input)
        st.subheader("There you go:")
        st.write(response)
    else:
        st.warning("Please enter a valid prompt.")
