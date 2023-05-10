import openai
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")
openai.api_key = API_KEY


def summarizeArticle(prompt):
    response = openai.Completion.create(
        engine = "text-davinci-003",
        max_tokens = 1000, #determine max words of the response
        prompt = prompt, 
        temperature = 0.5 #variation of responses (lowest 0 to 1 highest)
    ) 
    return response
    

if __name__ == "__main__":
    thedict = { "content_text": "Network Integrity Assurance Technologies (NiAT) Sdn Bhd organised a charity shopping event titled ‘Shopping Raya with NiAT’ for 10 underprivileged families to support their Raya preparation needs yesterday. Held at the Hua Ho Department Store in OneCity Shopping Centre in Salambigar, the event was organised as part of NiAT’s corporate social responsibility (CSR) initiative this year and promote volunteerism to give back to society by instilling in its employees a caring culture that aids those who are less fortunate. During the event, NiAT covered up to BND300 worth of necessities for each of the selected family. Over 20 NiAT staff members assisted the families with their grocery purchases. NiAT’s Chief Executive Officer Lim Ming Soon said “We believe it is essential to show happiness in the lives of others, and we intend to uphold this belief through the initiative. “It gives us great delight to contribute to the happiness of these families. We are also pleased to provide them with financial assistance and bring them the joy of Hari Raya so that they, too, may enjoy the upcoming festivities as much as everyone else”. The families were identified by Projek Feed, a social enterprise focussing on aiding financially-challenged families.    "} 

    prompt = "Give me the main points of this article in bullet point form, with a legend showing any abbreviations: '" + str(str(thedict["content_text"]).strip())+ "'"

    response = summarizeArticle(prompt)

    for choice in response.choices:
        print(choice.text)