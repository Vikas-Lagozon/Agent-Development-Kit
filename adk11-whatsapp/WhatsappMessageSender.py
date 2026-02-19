from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import os
import time
import urllib.parse
from typing import List

class WhatsAppAutomation:
    def __init__(self, headless: bool = True):
        """
        Initialize WhatsApp automation with specified mode
        
        Args:
            headless (bool): Whether to run in headless mode
        """
        self.headless = headless
        self.driver = None
        self.wait = None
    
    def __del__(self):
        """
        Destructor to ensure cleanup of resources when object is destroyed
        """
        try:
            self.cleanup()
        except Exception as e:
            print(f"Error in destructor cleanup: {str(e)}")
    
    def _create_chrome_options(self) -> Options:
        """Create and configure Chrome options"""
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        
        # Add user data directory to maintain session
        user_data_dir = os.path.join(os.getcwd(), "whatsapp_session")
        options.add_argument(f"--user-data-dir={user_data_dir}")
        
        return options
    
    def initialize_driver(self) -> None:
        """Initialize WebDriver with appropriate settings"""
        if self.driver is not None:
            return
            
        service = Service(ChromeDriverManager().install())
        options = self._create_chrome_options()
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 30)
    
    def send_message(self, phone_number: str, message: str) -> bool:
        """
        Send a single message
        
        Args:
            phone_number (str): Target phone number with country code
            message (str): Message to send
            
        Returns:
            bool: Success status of message sending
        """
        try:
            # Format phone number and message
            phone_number = phone_number.replace("+", "")
            encoded_message = urllib.parse.quote(message)
            
            # Construct and open WhatsApp Web URL
            whatsapp_url = f"https://web.whatsapp.com/send?phone={phone_number}&text={encoded_message}"
            self.driver.get(whatsapp_url)
            
            # Wait for and click send button
            send_button = self.wait.until(EC.presence_of_element_located((
                By.XPATH, "//span[@data-icon='send']"
            )))
            
            time.sleep(2)  # Wait for button to be truly clickable
            
            send_button = self.wait.until(EC.element_to_be_clickable((
                By.XPATH, "//span[@data-icon='send']"
            )))
            
            send_button.click()
            print("Message sent successfully!")
            
            time.sleep(2)  # Wait for message delivery
            return True
            
        except Exception as e:
            print(f"Error sending message: {str(e)}")
            return False
    
    def run_message_loop(self, phone: str, messages: List[str], delay: int = 10) -> None:
        """
        Run continuous message sending loop
        
        Args:
            phone (str): Target phone number
            messages (List[str]): List of messages to send
            delay (int): Delay between messages in seconds
        """
        try:
            print("Initializing WhatsApp Web in background...")
            self.initialize_driver()
            
            count = 0
            while True:
                print("\n===========================")
                print(f"Message #{count + 1} - Sending...")
                
                current_message = messages[count % len(messages)]
                success = self.send_message(phone, current_message)
                
                if success:
                    print(f"Waiting {delay} seconds before next message...")
                    time.sleep(delay)
                else:
                    print("Retrying in 30 seconds...")
                    time.sleep(30)
                
                count += 1
                
        except KeyboardInterrupt:
            print("\nStopping message sender...")
        except Exception as e:
            print(f"Fatal error occurred: {str(e)}")
        finally:
            self.cleanup()
    
    def cleanup(self) -> None:
        """Clean up resources"""
        if self.driver:
            try:
                print("Closing browser...")
                self.driver.quit()
            except Exception as e:
                print(f"Error while closing browser: {str(e)}")
            finally:
                self.driver = None
                self.wait = None
                print("Process completed!")


def main():
    # Example usage
    phone_number = "+919584224133"
    messages = ["Good Morning.", 
                "Good Afternoon.",
                "Good Night."]
    
    # Create WhatsApp automation instance and run
    whatsapp = WhatsAppAutomation(headless=True)
    whatsapp.run_message_loop(phone_number, messages, delay=5)

if __name__ == "__main__":
    main()


