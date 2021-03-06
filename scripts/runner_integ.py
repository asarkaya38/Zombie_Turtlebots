#!/usr/bin/env python
import rospy
import sys
from math import atan2, sqrt
from std_msgs.msg import String
from geometry_msgs.msg import Point,Twist
from nav_msgs.msg import Odometry
from tf.transformations import euler_from_quaternion

selfName = sys.argv[1]
zombieName = sys.argv[2]
safe_threshold = int(sys.argv[3])

# Define Global Constants
mainProgramRate = 1
num_safe_points = 16
run_multiplier = 2

class runner:
   # Class Initializer
   def __init__(self):

      # Define Class Variables
      self.vel_msg = Twist()
      self.self_position = Point()
      self.current_theta = 0
      self.zombie_position = Point()
      self.run_position = Point()
      self.safe_points = [[0]*2]*num_safe_points
      self.update_safe_zone()

      # Set up run point publisher
      self.run_point_pub = rospy.Publisher('/run_loc/', Point, queue_size=10)
      self.vel_pub = rospy.Publisher('/cmd_vel/', Twist, queue_size=10)

      # Init Node
      rospy.init_node('runner', anonymous=True)

      self.rate = rospy.Rate(mainProgramRate)

   # Get self position
   def get_odom_self(self):
      odom_data = rospy.wait_for_message('/odom/', Odometry)
      self.self_position = odom_data.pose.pose.position
      self.self_position.x = round(self.self_position.x,4)
      self.self_position.y = round(self.self_position.y,4)
      quaternion = (
         odom_data.pose.pose.orientation.x,
         odom_data.pose.pose.orientation.y,
         odom_data.pose.pose.orientation.z,
         odom_data.pose.pose.orientation.w
      )
      euler = euler_from_quaternion(quaternion)
      self.current_theta = round(euler[2],4)
      self.update_safe_zone()
   
   # Get Zombie Position
   def get_odom_zombie(self):
      odom_data = rospy.wait_for_message('/' + zombieName + '/odom/', Odometry)
      self.zombie_position = odom_data.pose.pose.position
      self.zombie_position.x = round(self.zombie_position.x,4)
      self.zombie_position.y = round(self.zombie_position.y,4)

   # Re-define safe zone based on runner current location
   # There's probably a more elegant way to do this
   def update_safe_zone(self):
      self.safe_points[0] = [self.self_position.x+(-safe_threshold/2),self.self_position.y+safe_threshold]
      self.safe_points[1] = [self.self_position.x+(-safe_threshold),self.self_position.y+safe_threshold]
      self.safe_points[2] = [self.self_position.x+(-safe_threshold),self.self_position.y+(safe_threshold/2)]
      self.safe_points[3] = [self.self_position.x+(-safe_threshold),self.self_position.y]
      self.safe_points[4] = [self.self_position.x+(-safe_threshold),self.self_position.y+(-safe_threshold/2)]
      self.safe_points[5] = [self.self_position.x+(-safe_threshold),self.self_position.y+(-safe_threshold)]
      self.safe_points[6] = [self.self_position.x+(-safe_threshold/2),self.self_position.y+(-safe_threshold)]
      self.safe_points[7] = [self.self_position.x,self.self_position.y+(-safe_threshold)]
      self.safe_points[8] = [self.self_position.x+(safe_threshold/2),self.self_position.y+(-safe_threshold)]
      self.safe_points[9] = [self.self_position.x+safe_threshold,self.self_position.y+(-safe_threshold)]
      self.safe_points[10] = [self.self_position.x+safe_threshold,self.self_position.y+(-safe_threshold/2)]
      self.safe_points[11] = [self.self_position.x+safe_threshold,self.self_position.y]
      self.safe_points[12] = [self.self_position.x+safe_threshold,self.self_position.y+(safe_threshold/2)]
      self.safe_points[13] = [self.self_position.x+safe_threshold,self.self_position.y+safe_threshold]
      self.safe_points[14] = [self.self_position.x+(safe_threshold/2),self.self_position.y+safe_threshold]
      self.safe_points[15] = [self.self_position.x,self.self_position.y+safe_threshold]
      self.max_safe_x = self.self_position.x+safe_threshold
      self.min_safe_x = self.self_position.x-safe_threshold
      self.max_safe_y = self.self_position.x+safe_threshold
      self.min_safe_y = self.self_position.x-safe_threshold

   # Find the next safe point to move to
   def find_safe_point(self):
      max_euclidean = 0
      max_index = 0
      current_euclidean = 0   
      for i in range(num_safe_points):
         current_euclidean = abs(self.euclidean_distance(self.self_position,self.zombie_position))
         if current_euclidean > max_euclidean:
            max_euclidean = current_euclidean
            max_index = i

      self.run_position.x = self.safe_points[i][0]
      self.run_position.y = self.safe_points[i][1]
      self.run_point_pub.publish(self.run_position)

   # Euclidean distance between current pose and the goal.
   # http://wiki.ros.org/turtlesim/Tutorials/Go%20to%20Goal
   def euclidean_distance(self,a,b):
      return sqrt(pow((b.x - a.x), 2) + pow((b.y - a.y), 2))

   # Calculate linear velocity to move towards goal
   # http://wiki.ros.org/turtlesim/Tutorials/Go%20to%20Goal
   def linear_vel(self,a,b,constant=0.1):
      return constant * self.euclidean_distance(a,b)

   # Calculate difference in angle between goal and current pose
   # http://wiki.ros.org/turtlesim/Tutorials/Go%20to%20Goal   
   def steering_angle(self,a,b):
      return atan2(b.y - a.y, b.x - a.x)

   # Calculate angular velocity to move towards goal
   # http://wiki.ros.org/turtlesim/Tutorials/Go%20to%20Goal
   def angular_vel(self,a,b,theta,constant=1):
      return constant * (self.steering_angle(a,b) - theta)

   # Move to goal point
   def decide_motion(self):
      if (self.euclidean_distance(self.self_position,self.run_position) >= 1):
         self.vel_msg.linear.x = self.linear_vel(self.self_position,self.run_position)
         self.vel_msg.angular.z = self.angular_vel(self.self_position,self.run_position,self.current_theta)           
      else:
         self.vel_msg.linear.x = 0.0
         self.vel_msg.angular.z = 0.0

      self.vel_pub.publish(self.vel_msg)

   # Decide if the given zombie is in the current safe zone
   def zombie_in_safe_zone(self,zombie_point):
      if zombie_point.x < self.max_safe_x and zombie_point.x > self.min_safe_x and zombie_point.y < self.max_safe_y and zombie_point.y > self.min_safe_y:
         return True
      else:
         return False

   # Main Program
   def program(self):
      while not rospy.is_shutdown():
         self.get_odom_self()
         self.get_odom_zombie()
         self.find_safe_point()
         #self.decide_motion()
         self.rate.sleep()


if __name__ == '__main__':
   try:
      robot = runner()
      robot.program()
   except rospy.ROSInterruptException:
      pass
